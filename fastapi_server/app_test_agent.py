import sys
sys.path.append('/home/root/coorGen')
import asyncio
import uuid
import json

from typing import Any
from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi_server.core.redis import init_redis, close_redis, get_redis_client
from pydantic import BaseModel
from contextlib import asynccontextmanager
from agent_main.agent import make_graph as make_graph_deploy
from agent_locate.agent import make_graph as make_graph_delete
from agent_retrieve.agent import make_graph as make_graph_retrieve
from project.app import TestAgent
from redis.asyncio import Redis
from langchain_redis import RedisChatMessageHistory

@asynccontextmanager  # lifespan替代startup和shutdown
async def lifespan(app: FastAPI):
    # Init DB (optional)
    app.state.graphs = {}
    app.state.graphs['deploy'] = await make_graph_deploy(True)
    app.state.graphs['delete'] = await make_graph_delete(True)
    app.state.graphs['retrieve'] = await make_graph_retrieve(True)
    await init_redis("redis://localhost:6379")

    print('\n', '='*100, '\n')
    yield
    print('\n', '='*100, '\n')
    await close_redis()

app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

task_status = {}
message_queue = asyncio.Queue()  # SSE
task_connections: dict[str, list[WebSocket]] = {}  # {main_task_id: [WebSocket1, WebSocket2, ...]}
task_ready_flags: dict[str, asyncio.Event] = {}
task_map_table: dict[str, str] = {}

class AgentInput(BaseModel):
    order_list: list[str] = None
    configs: list[dict[str, Any]]|list[str] = None
    agent: str = "agent_main"

@app.post("/run_test_agent")
async def run_test_agent(input: AgentInput, request: Request, r: Redis=Depends(get_redis_client)):  # 每个主任务创建一个redis连接

    main_task_id = str(uuid.uuid4())  # 生成任务组 ID
    # 获取你要传入的全局参数（你可以换成你项目中具体的调用方式）
    graphs = request.app.state.graphs  # 你自己设定的 graph

    # 初始化同步事件
    event = asyncio.Event()
    task_ready_flags[main_task_id] = event  # 注册任务等待事件
    
    # 创建异步任务
    async def runner():
        await event.wait()  # 等待 WebSocket 设置好 task_connections
        try:
            await TestAgent(
                graphs=graphs,
                order_list=getattr(input, 'order_list'),
                agent=getattr(input, 'agent'),
                configs=getattr(input, 'configs'),
                mode='fastapi',
                message_queue=message_queue,
                task_connections=task_connections,
                task_id=main_task_id,
                task_status=task_status,
                redis_client=r,
            ).main()
            task_status[main_task_id] = "done"
        except Exception as e:
            task_status[main_task_id] = "error"
            raise e

    asyncio.create_task(runner())
    return {"task_id": main_task_id, "task_name": '\n'.join(input.order_list) if input.order_list else '未接收到主任务'}

class MonitoredWebSocket:
    def __init__(self, websocket, task_id, task_name):
        self.websocket = websocket
        self.task_id = task_id
        self.task_name = task_name
        self.is_closed = False

    async def send_text(self, text):
        # print(f"Sending to task {self.task_id}: {text}")  # 监控日志
        await self.websocket.send_text(text)

    async def send_json(self, json):
        # print(f"Sending to task {self.task_id}: {json}")  # 监控日志
        await self.websocket.send_json(json)  # 保证 先发消息，再关闭连接

        if json.get('type') == 'done':
            print(f"任务 {self.task_name} 完成！")

        elif json.get('type') == 'progress':
            print(f"任务 {self.task_name} 进度: {json.get('progress')}%")

        elif json.get('type') == 'close':
            print(f"任务 {self.task_name} 关闭websocket...")
            task_connections[self.task_id].remove(self)
            await self.close()

    async def close(self):
        if not self.is_closed:
            print(f"Closing connection for task {self.task_name}")
            self.is_closed = True
            await self.websocket.close()

@app.websocket("/ws")  # 前端每次new一个WebSocket连接，就会创建一个websocket连接，这里就是client端
async def websocket_endpoint(websocket: WebSocket, task_id: str, task_name: str):  # 会创建main_task_id以及sub_task_id
    monitored_ws = MonitoredWebSocket(websocket, task_id, task_name)
    await monitored_ws.websocket.accept()

    if task_id not in task_connections:  # 没有创建过该任务的连接
        task_connections[task_id] = []
    task_connections[task_id].append(monitored_ws)
    task_map_table[task_id] = task_name
    
    # 通知 runner 连接已准备好
    if task_id in task_ready_flags:
        task_ready_flags[task_id].set()
    try:
        while True:
            await websocket.send_text("❤")  # 保持连接/心跳
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        if task_id in task_connections and monitored_ws in task_connections[task_id]:  # 递进式判断
            task_connections[task_id].remove(monitored_ws)
        print(f"WebSocket disconnected for task {task_name}")
    except Exception:
        pass
    finally:
        try:
            print(f"Final task_connections: \n{json.dumps(task_connections, indent=4, ensure_ascii=False)}")
        except Exception:
            pass
        finally:
            if task_id in task_connections:
                task_connections.pop(task_id)
                task_rest = {i:task_map_table[i] for i in list(task_connections.keys())}
                print(f"还剩任务: \n{json.dumps(task_rest, indent=4, ensure_ascii=False)}")

@app.get("/sse")
async def sse(request: Request):
    async def event_stream():
        while not await request.is_disconnected():
            data = await message_queue.get()
            yield f"data: {data}\n\n"
    return StreamingResponse(event_stream(), media_type="text/event-stream")

# 首页：返回带有 JS 的 HTML 页面
@app.get("/", response_class=HTMLResponse)
async def homepage(request: Request):
    return templates.TemplateResponse("homepage_ws.html", {"request": request, "title": "欢迎使用 FastAPI"})

@app.get("/get_result/{task_id}")
async def get_result(task_id: str):
    return {"status": task_status.get(task_id, "not_found")}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
