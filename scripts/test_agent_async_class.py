import re
import asyncio
import contextvars
import uuid
import itertools
import geopandas as gpd
import numpy as np
import pandas as pd
import time
import copy
import json

from IPython.display import display, Markdown
from scripts.flatten import flatten
from scripts.merge_dict import merge_dict
# from scripts.stream_output import stream_output_graph
from scripts.time_travel import get_state_by_config, get_states
from scripts.file_op import fileop
from scripts.time_travel import print_state
from agent_locate.utils.schema import merge_delete_infos_json
from fastapi.decorator import TaskMeta, async_decorator, sync_decorator

class test_agent:
    def __init__(self, **kwargs):
        # 外部变量
        self.graph = kwargs.get('graph', None)
        self.merge_result = kwargs.get('merge_result', merge_delete_infos_json)
        self.order_list = kwargs.get('order_list', [])
        self.count = kwargs.get('count', 999)
        self.agent = kwargs.get('agent', 'agent_main')
        self.configs = kwargs.get('configs') if kwargs.get('configs') and kwargs.get('configs')[0] else []
        self.mode = kwargs.get('mode', 'fastapi')
        # self.wait_for_connection = kwargs.get('wait_for_connection', None)
        # 内部变量
        self._result_saver = self.ConversationContext(self)
        self._task_results_queue = asyncio.Queue()
        self._error_ctx = contextvars.ContextVar('error_ctx')
        self._task_results_ctx = contextvars.ContextVar('task_results_ctx')
        self._handlers: dict[str, callable] = {}
        self._active_workers = set()  # 保存活跃 worker 协程
        self._MAX_WORKERS = 10
        # fastapi
        self._message_queue = kwargs.get('message_queue', [])  # SSE
        self._task_connections = kwargs.get('task_connections', [])  # WebSocket
        self._task_id = kwargs.get('task_id', '')
        self._task_status = kwargs.get('task_status', {})
        self._communication_mode = 'websocket'

    async def main(self):
        task_inputs_queue = asyncio.Queue()
        error_ctx = []
        token_error = self._error_ctx.set(error_ctx)

        manager_task = asyncio.create_task(self.manager(task_inputs_queue))

        await asyncio.create_task(self.boss(task_inputs_queue))  # 等待boss生成完毕

        await task_inputs_queue.join()  # 等待所有任务完成

        for active_worker in self._active_workers:  # 显式取消所有 worker
            active_worker.cancel()
        await asyncio.gather(*self._active_workers, return_exceptions=True)

        manager_task.cancel()  # 关闭manager
        await asyncio.gather(manager_task, return_exceptions=True)  # 不会raise报错,但会关闭manager

        await self.send_result(self._task_id, {
            "type": "done",
            "task_id": self._task_id,
            "task_name": self.order_list,
        })

        if self._error_ctx.get():  # 最后统一收集错误信息
            await self.send_result(self._task_id, "📋 Collected errors:")
            for err in self._error_ctx.get():
                await self.send_result(self._task_id, f"  • {err}")
        self._error_ctx.reset(token_error)

    async def manager(self, queue):
        sem = asyncio.Semaphore(self._MAX_WORKERS)
        while True:
            await asyncio.sleep(0.1)

            # 如果有任务尚未被 get，并且还有 worker 空位
            needed_workers = queue.qsize()
            available_slots = self._MAX_WORKERS - len(self._active_workers)
            to_spawn = min(needed_workers, available_slots)

            for _ in range(to_spawn):
                self._active_workers.add(asyncio.create_task(self.worker(queue, sem)))

    async def worker(self, queue, sem):
        async with sem:
            try:
                while True:
                    task_input = await queue.get()  # cancel只有在最底层的await才会捕获,而这个await

                    # 任务信息
                    task_id = task_input.get('task_id', "unknown")
                    task_name = task_input.get('task_name', "unknown")

                    # 参数信息
                    graph_input = task_input.get('graph_input', None)
                    config = task_input.get('config', {
                            "configurable": {
                                "thread_id": str(uuid.uuid4())
                            }
                        })

                    # 任务准备
                    await self.send_result(self._task_id, {
                        "type": "init",
                        "task_id": task_id,
                        "task_name": task_name
                    })
                    await self.wait_for_connection(task_id)  # 等待子任务连接建立

                    try:
                        # 任务执行
                        previous_time = time.time()
                        state_output = await self.stream_output_graph(graph_input, config, task_name)
                        iteration_time = time.time() - previous_time
                        await self.send_result(self._task_id, f"✅ {task_name} 耗时: {iteration_time:.8f} 秒")

                        if self.configs:
                            self._result_saver.update_history(task_id, task_name, state_output)  # 有configs，进入更新模式
                        else:
                            self._result_saver.add_history(task_id, task_name, state_output)  # 无configs，进入运行模式

                        result_merged = self.merge_all_results([state_output])
                        result_flattened = self.flatten_and_tag(result_merged)
                        self.downstream(result_flattened, task_name, agent=self.agent)
                    except Exception as e:
                        error = f"❌ {task_name} Caught: {e}"
                        self._error_ctx.get().append(error)
                        print(error)
                        await self.send_result(self._task_id, error)
                    finally:
                        # await self.send_result(task_id, {
                        #     "type": "done",
                        #     "task_id": task_id,
                        #     "task_name": task_name,
                        # })
                        queue.task_done()
            except asyncio.CancelledError:  # 只有在await的时候才会捕获异常
                raise asyncio.CancelledError

    async def boss(self, queue):
        if self.configs:
            for config in self.configs:
                print("="*50, "part1", "="*50)
                name = get_state_by_config(self.graph, config)['values']['messages'][0].content
                order = {
                    'task_id': config['configurable']['thread_id'],
                    'task_name': name,
                    'graph_input': None,
                    'config': config
                }
                print("="*50, "part2", "="*50)
                await queue.put(order)
        else:
            order_db = np.array(self.order_list)
            mask = np.array([True] * len(order_db))
            while np.sum(mask) > 0 and self.count > 0:
                self.count -= 1
                indices = next(iter(np.where(mask)[0].tolist()))
                mask[indices] = False
                order = order_db[indices].tolist()

                task_names = [seg.strip() for seg in re.split(r"[;；]", order) if seg.strip()]
                for task_name in task_names:
                    task_id = str(uuid.uuid4())
                    order = {
                        'task_id': task_id,
                        'task_name': task_name,
                        'graph_input': {"messages": [("user", task_name)]},
                        'config': {
                            "configurable": {
                                "thread_id": task_id
                            }
                        }
                    }
                    await queue.put(order)

    async def stream_output_graph(self, 
        graph_input, 
        config={'configurable': {'thread_id': str(uuid.uuid4())}}, 
        graph_name='MyGraph'
        ):
        turn = 0
        previous_time = time.time()
        async for node, state_raw in self.graph.astream(
            graph_input,
            subgraphs=True,
            stream_mode='debug',
            config=config
        ):
            state = state_raw['payload']
            fileop.save_any_append(state, f'datasets/{self.mode}/{graph_name[:5]}.py')

            if not state.get('values', {}).get('messages', []):
                continue

            await self.print_state(config['configurable']['thread_id'], state)

            turn += 1
            current_time = time.time()
            iteration_time = current_time - previous_time
            await self.send_result(config['configurable']['thread_id'], f"==={graph_name}=== 第{turn}次运行\n {node} 耗时: {iteration_time:.8f} 秒")
            previous_time = current_time

        result = state.get('values', {}).get('final_response')
        return result

    async def gather_tasks(self, tasks):
        try:
            responses = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=240)  # 等待所有任务完成
        except asyncio.TimeoutError:
            raise ValueError("⏲ 任务超时！")

        result_list = []
        for task_obj, res in zip(tasks, responses):
            task_name = task_obj.get_name()
            if isinstance(res, Exception):
                # raise ValueError(f"[{task_name}] 出错: {res}")
                await self.send_result(self._task_id, f"[{task_name}] 出错: {res}")
            else:
                await self.send_result(self._task_id, f"[{task_name}] 成功")
                if self.configs:
                    self._result_saver.update_history(str(res[0]), task_name, res[1])
                else:
                    self._result_saver.add_history(str(res[0]), task_name, res[1])
                result_list.append(res[1])
        return result_list

    def merge_all_results(self, result_list):
        result = {}
        for r in itertools.chain.from_iterable(result_list):
            result = self.merge_result(result, r)
        return result

    def flatten_and_tag(self, result):
        teams = []
        if result.get('red') not in ['null', None]:
            teams.append(('红方', result['red']))
        if result.get('blue') not in ['null', None]:
            teams.append(('蓝方', result['blue']))

        d = {}
        old_len = 0
        for color, team in teams:
            for flat in flatten(team):
                d = merge_dict(d, flat, color)
            d_team = d.get('team', [])
            d_team.extend([color] * (len(d[next(iter(d))]) - old_len))
            d['team'] = d_team
            old_len = len(d[next(iter(d))])
        return d

    def downstream(self, d, order, agent):
        ## agent_main
        if agent=='agent_main':
            marker_kwds = {'radius':10, 'draggable':True, 'fill':True}
            def my_colormap(value):
                if value == '蓝方':
                    return "blue"
                elif value == '红方':
                    return "red"
                else:
                    return "green"
            gdf = gpd.GeoDataFrame(d, crs="EPSG:4326").sort_values(by='team', ignore_index=True, kind='stable')
            # clear_output()
            display(Markdown(f'## <p style="text-align: center;">**{order}**</p>'))
            display(gdf)
            display(gdf.explore(column='team', cmap=[my_colormap(value) for value in gdf['team'].unique()], marker_type='circle_marker', marker_kwds = marker_kwds, tooltip = ['team', 'name']))

        ## agent_locate
        if agent=='agent_locate':
            self.send_result(self._task_id, f"\n==== 已删除装备 ====")
            for name, id in zip(d['name'], d['id']):
                self.send_result(self._task_id, f"{name}, {id}")

    async def wait_for_connection(self, task_id: str, timeout: float = 5.0):
        if self.mode == 'fastapi':
            for _ in range(int(timeout * 10)):  # 10 次每次 100ms，总共最多等待 5 秒
                if task_id in self._task_connections:
                    return
                await asyncio.sleep(0.1)
            raise TimeoutError("WebSocket not connected in time")

    async def print_state(self, task_id, state):
        message = state['values']['messages'][-1]
        content = message.pretty_repr()

        await self.send_result(task_id, f'{content}\n')
        if len(state['values']) > 1:
            await self.send_result(task_id, '==其他变量==')
            rest_values = copy.deepcopy(state['values'])
            rest_values.pop('messages')
            await self.send_result(task_id, f'{json.dumps(rest_values, indent=4, ensure_ascii=False)}\n')

        try:
            node_name = next(iter(state['metadata']['writes']))
        except:
            node_name = 'human'
        if node_name == '__start__':  # 强行纠正一个机制bug，问题不大
            node_name = 'human'
        await self.send_result(task_id, f'==当前节点==\n{node_name}')

        await self.send_result(task_id, f'==当前config==\n{json.dumps({"configurable":state["config"]["configurable"]}, indent=4, ensure_ascii=False)}')

    async def send_result(self, task_id, result):
        if self.mode == 'jupyter':
            print(result)
        else:
            if self._communication_mode == 'sse':
                # SSE
                await self._message_queue.put(result.replace('\n', 'temp'))
            elif self._communication_mode == 'websocket':
                # WebSocket
                websockets = self._task_connections.get(task_id, [])  # 由于没有事先创建好sub_task的通道，因此这里为空
                
                if websockets:
                    for ws in websockets:
                        try:
                            if isinstance(result, str):
                                await ws.send_text(result.replace('\n', 'temp'))
                            elif isinstance(result, dict):
                                await ws.send_json(result)
                        except:
                            pass


    class ConversationContext:
        def __init__(self, test_agent):
            self.user_name = None
            self.history = pd.DataFrame(columns=['thread_id', 'task_name', 'task_result'])
            self.test_agent = test_agent
        def add_history(self, thread_id, task_name, task_result):
            self.history.loc[len(self.history)] = [thread_id, task_name, task_result]
        def update_history(self, thread_id, task_name, task_result):
            self.add_history(thread_id, task_name, task_result)
            self.history.drop_duplicates(subset='thread_id', keep='last', inplace=True)
        def print(self):
            self.test_agent.send_result(self.test_agent._task_id, self.history.to_string(index=False))

    class TaskCollection(metaclass=TaskMeta):
        """同步和异步方法的集合类"""
        
        def __init__(self):
            self._tasks = {}
            self._register_tasks()
        
        def _register_tasks(self):
            """注册所有标记了任务标签的方法"""
            for name in dir(self):
                if not name.startswith('_'):
                    attr = getattr(self, name)
                    if callable(attr):
                        self._tasks[name] = attr
        
        async def execute(self, task_name: str, *args, **kwargs):
            """执行指定任务
            
            Args:
                task_name: 方法名/任务标签
                *args: 位置参数
                **kwargs: 关键字参数
                
            Returns:
                方法的返回结果
            """
            if task_name not in self._tasks:
                raise ValueError(f"未知任务: {task_name}")
            
            task = self._tasks[task_name]
            
            # 如果是协程函数，异步执行
            if asyncio.iscoroutinefunction(task):
                return await task(*args, **kwargs)
            # 否则同步执行
            return task(*args, **kwargs)
        
        # 下面是示例任务方法
        
        @staticmethod
        def add(a: int, b: int) -> int:
            """同步加法"""
            return a + b
        
        @staticmethod
        async def async_multiply(a: int, b: int) -> int:
            """异步乘法"""
            await asyncio.sleep(0.1)  # 模拟异步操作
            return a * b
        
        def greet(self, name: str) -> str:
            """同步问候"""
            return f"Hello, {name}!"
        
        async def async_countdown(self, n: int) -> None:
            """异步倒计时"""
            for i in range(n, 0, -1):
                print(i)
                await asyncio.sleep(1)
            print("Done!")





