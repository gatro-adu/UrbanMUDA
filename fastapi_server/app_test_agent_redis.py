import sys
sys.path.append('/home/root/coorGen')
import asyncio
import uuid
import json
import redis.asyncio as redis

from fastapi import FastAPI, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import StreamingResponse, HTMLResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Any
from contextlib import asynccontextmanager
from agent_main.agent import make_graph
from agent_locate.utils.schema import merge_delete_infos_json
# 你原本的 test_agent 函数
from scripts.test_agent_async_class import test_agent

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Init DB (optional)
    app.state.graph = await make_graph(True)
    print('\n', '='*100, '\n')
    yield

app = FastAPI(lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

task_status = {}
message_queue = asyncio.Queue()  # SSE
task_connections: dict[str, list[WebSocket]] = {}  # {main_task_id: [WebSocket1, WebSocket2, ...]}
task_ready_flags: dict[str, asyncio.Event] = {}
task_map_table: dict[str, str] = {}

async def wait_for_connection_pubsub(task_id: str, timeout=30):  # 通过订阅模式等待是否任务是否已进入redis
    # 先检查标志位，避免在订阅前就已发送连接建立
    if await r.get(f"task:{task_id}:ready_flag") == b"1":
        return True
    
    # 第二步：确认未就绪后，再订阅频道（避免错过通知）
    pubsub = r.pubsub()
    await pubsub.subscribe(f"task:{task_id}:ready_channel")

    # 第三步：双重检查（防止订阅完成前恰好就绪）
    if await r.get(f"task:{task_id}:ready_flag") == b"1":
        await pubsub.unsubscribe(f"task:{task_id}:ready_channel")
        return True

    try:
        async with asyncio.timeout(timeout):  # 超时上下文管理器
            async for message in pubsub.listen():
                if message["type"] == "message" and message["data"] == b"1":
                    return True
    except TimeoutError:
        print(f"等待消息超时（{timeout}秒）")
        return False
    finally:
        await pubsub.unsubscribe(f"task:{task_id}:ready_channel")

class AgentInput(BaseModel):
    order_list: list[str] = None
    configs: list[dict[str, Any]]|list[str] = None
    agent: str = "agent_main"

@app.post("/run_test_agent")
async def run_test_agent(input: AgentInput, request: Request):
    main_task_id = str(uuid.uuid4())  # 生成任务组 ID
    # 获取你要传入的全局参数（你可以换成你项目中具体的调用方式）
    graph = request.app.state.graph  # 你自己设定的 graph

    # 初始化同步事件
    # event = asyncio.Event()
    # task_ready_flags[main_task_id] = event  # 注册任务等待事件
    
    # 创建异步任务
    async def runner():
        # await event.wait()  # 等待 WebSocket 设置好 task_connections
        await wait_for_connection_pubsub(main_task_id)  # 等待 WebSocket 设置好 task_connections
        try:
            await test_agent(
                graph=graph,
                order_list=getattr(input, 'order_list'),
                agent=getattr(input, 'agent'),
                configs=getattr(input, 'configs'),
                mode='fastapi',
                message_queue=message_queue,
                task_connections=task_connections,
                task_id=main_task_id,
                task_status=task_status,
                wait_for_connection=wait_for_connection_pubsub
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
            task_connections[self.task_id].remove(self)
            await self.close()
        elif json.get('type') == 'progress':
            print(f"任务 {self.task_name} 进度: {json.get('progress')}%")

    async def close(self):
        if not self.is_closed:
            print(f"Closing connection for task {self.task_name}")
            self.is_closed = True
            await self.websocket.close()

redis_pool = redis.ConnectionPool.from_url("redis://localhost:6379/0")  # 0是数据库编号
r = redis.Redis(connection_pool=redis_pool)  # 创建一个异步redis客户端
class RedisManager:
    def __init__(self, task_id: str, ws: MonitoredWebSocket):
        self.task_id = task_id
        self.ws = ws
        redis_pool
    
    # 使用Redis替代内存存储
    async def get_task_connections(self) -> list[dict]:
        """从Redis获取任务的连接列表"""
        connections = await r.lrange(f"task:{self.task_id}:connections", 0, -1)
        return [json.loads(conn) for conn in connections]

    async def add_task_connection(self):
        """添加连接到Redis"""
        conn_data = {
            "task_id": self.ws.task_id,
            "task_name": self.ws.task_name,
            "connected_at": str(self.ws.websocket.client)
        }
        await r.rpush(f"task:{self.task_id}:connections", json.dumps(conn_data))  # rpush：右插入到connections列表中
        await r.expire(f"task:{self.task_id}:connections", 3600)  # 设置过期时间
        await r.hset("task:map", self.task_id, self.ws.task_name)  # hset：设置task:map全局表的key为self.task_id，value为self.ws.task_name
    
    async def remove_task_connection(self):
        """从Redis移除连接"""
        connections = await self.get_task_connections()
        updated_connections = [
            conn for conn in connections 
            if conn["task_id"] != self.ws.task_id
        ]
        
        # 更新Redis中的连接列表
        await r.delete(f"task:{self.task_id}:connections")
        if updated_connections:
            await r.rpush(f"task:{self.task_id}:connections", *[json.dumps(c) for c in updated_connections])
        else:
            # 如果没有连接了，清理相关键
            await r.hdel("task:map", self.task_id)
            await r.delete(f"task:{self.task_id}:connections")
            await r.delete(f"task:{self.task_id}:ready_flag")
    
    async def set_task_ready(self):
        """设置任务准备就绪标志"""
        await r.set(f"task:{self.task_id}:ready_flag", "1", ex=3600)  # 设置该任务的ready_flag为1
        await r.publish(f"task:{self.task_id}:ready_channel", "1")  # 广播该任务已就绪

    async def is_task_ready(self) -> bool:
        """检查任务是否准备就绪"""
        return await r.exists(f"task:{self.task_id}:ready_flag") == 1

@app.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket, 
    task_id: str, 
    task_name: str
    ):
    monitored_ws = MonitoredWebSocket(websocket, task_id, task_name)
    await monitored_ws.websocket.accept()

    redis_manager = RedisManager(task_id, monitored_ws)
    # 添加连接到Redis
    await redis_manager.add_task_connection()
    
    # 通知runner连接已准备好
    await task_ready_flags[task_id].set()
    await redis_manager.set_task_ready()
    
    try:
        while True:
            await websocket.send_text("❤")
            await asyncio.sleep(30)
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for task {task_name}")
    except Exception as e:
        print(f"WebSocket error for task {task_name}: {str(e)}")
    finally:
        # 清理连接
        await redis_manager.remove_task_connection()
        
        # 打印剩余任务状态
        remaining_tasks = await r.hgetall("task:map")
        print(f"剩余任务: {json.dumps({k.decode(): v.decode() for k, v in remaining_tasks.items()}, indent=4, ensure_ascii=False)}")

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
