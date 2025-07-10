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
from scripts.workflow_struct import struct_agent
from scripts.convert import convert
from scripts.time_travel import update_state_by_config
from project.utils.result_merge import merge_delete_infos_json
from project.utils.decor import TaskMeta, register_method
from project.utils.task_type_schema import examples, TaskTypeRouter
from langchain_redis import RedisChatMessageHistory

class TestAgent:
    def __init__(self, **kwargs):
        # 外部变量
        self.graphs = kwargs.get('graphs', None)
        self.merge_result = kwargs.get('merge_result', merge_delete_infos_json)
        self.order_list = kwargs.get('order_list', [])
        self.count = kwargs.get('count', 999)
        self.configs = kwargs.get('configs') if kwargs.get('configs') and kwargs.get('configs')[0] else []
        self.mode = kwargs.get('mode', 'fastapi')
        
        # 内部变量
        self._result_saver = self.ConversationContext(self)
        self._task_collection = self.TaskCollection(self)._method_map
        self._task_results_queue = asyncio.Queue()
        self._error_ctx = contextvars.ContextVar('error_ctx')
        self._task_ctx = contextvars.ContextVar('task_ctx')
        self._handlers: dict[str, callable] = {}
        self._active_workers = set()  # 保存活跃 worker 协程
        self._MAX_WORKERS = 10
        self._TIMEOUT = 240
        
        # fastapi
        self._message_queue = kwargs.get('message_queue', [])  # SSE
        self._task_connections = kwargs.get('task_connections', [])  # WebSocket
        self._task_id = kwargs.get('task_id', '')
        self._task_status = kwargs.get('task_status', {})
        self._communication_mode = 'websocket'

        # redis
        self._redis_client = kwargs.get('redis_client', None)
        self._history_redis_ctx = contextvars.ContextVar('history_redis_ctx')
        
    async def main(self):
        task_inputs_queue = asyncio.Queue()
        error_ctx = []
        token_error = self._error_ctx.set(error_ctx)

        manager_task = asyncio.create_task(self.manager(task_inputs_queue))

        previous_time = time.time()
        await asyncio.create_task(self.boss(task_inputs_queue))  # 等待boss生成完毕
        await task_inputs_queue.join()  # 等待所有任务完成

        for active_worker in self._active_workers:  # 显式取消所有 worker
            active_worker.cancel()
        await asyncio.gather(*self._active_workers, return_exceptions=True)

        manager_task.cancel()  # 关闭manager
        await asyncio.gather(manager_task, return_exceptions=True)  # 不会raise报错,但会关闭manager

        iteration_time = time.time() - previous_time
        print('='*50, f"任务结束", '='*50)
        print(f"✅ 该任务耗时: {iteration_time:.8f} 秒")
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
                task = asyncio.create_task(self.worker(queue, sem))
                self._active_workers.add(task)
                asyncio.create_task(self.remove_task_after_timeout(task))

    async def worker(self, queue, sem):
        async with sem:
            try:
                while True:
                    task_input = await queue.get()  # cancel只有在最底层的await才会捕获,而这个await

                    # 任务信息
                    task_id = task_input.get('task_id', "unknown")
                    task_name = task_input.get('task_name', "unknown")
                    task_type = task_input.get('task_type', "unknown")
                    # task_type = await self._redis_client.hget(f"task:{task_id}", 'task_type')

                    # 参数信息
                    graph_input = json.loads(task_input.get('graph_input'))
                    config = json.loads(task_input.get('config'))

                    # 任务准备
                    # 获取当前任务并修改名称
                    current_task = asyncio.current_task()
                    if current_task:  # 确保当前在任务上下文中
                        current_task.set_name(task_name)
                        current_task.task_id = task_id
                    await self.send_result(self._task_id, {
                        "type": "init",
                        "task_id": task_id,
                        "task_name": task_name
                    })
                    await self.wait_for_connection(task_id)  # 等待子任务连接建立

                    # 对话记录保存
                    self._history_redis_ctx.set(RedisChatMessageHistory(
                        session_id=task_id,
                        redis_url="redis://localhost:6379",
                        ttl=3600,  # Expire chat history after 1 hour
                        # index_name=f"task:{task_id}"
                    ))

                    try:
                        # 任务执行
                        previous_time = time.time()
                        state_output = await self._task_collection[task_type](
                            graph_input=graph_input,
                            graph_name=task_name,
                            config=config,
                        )
                        iteration_time = time.time() - previous_time
                        await self.send_result(self._task_id, f"✅ {task_name} 耗时: {iteration_time:.8f} 秒")

                        # 结果保存
                        self._task_ctx.set({
                            "task_id": task_id, 
                            "task_name": task_name, 
                            "task_type": task_type, 
                            "task_result": state_output,
                        })
                        if self.configs:
                            self._result_saver.update_history(task_id, task_name, state_output)  # 有configs，进入更新模式
                        else:
                            self._result_saver.add_history(task_id, task_name, state_output)  # 无configs，进入运行模式

                        # 下游任务
                        result_merged = self.merge_all_results([state_output])
                        result_flattened = self.flatten_and_tag(result_merged)
                        self.downstream(result_flattened, task_name)
                    except Exception as e:
                        error = f"❌ {task_name} Caught: {e}"
                        self._error_ctx.get().append(error)
                        print(error)
                        await self.send_result(self._task_id, error)
                    finally:
                        # 不要关闭worker
                        await self.send_result(task_id, {
                            "type": "done",
                            "task_id": task_id,
                            "task_name": task_name,
                        })
                        queue.task_done()
            except asyncio.CancelledError:  # 只有在await的时候才会捕获异常
                raise asyncio.CancelledError

    async def boss(self, queue):
        if self.configs:
            for config in self.configs:
                print("="*50, "part1", "="*50)
                task_type = await self._redis_client.hget(f"task:{config['configurable']['thread_id']}", 'task_type')
                graph = self.graphs[task_type]
                new_values = {"messages": [("user", self.order_list[0])]}
                new_config = update_state_by_config(graph, config, new_values)
                task_name = get_state_by_config(graph, new_config)['values']['messages'][0].content
                data = {
                    'task_id': config['configurable']['thread_id'],
                    'task_name': task_name,
                    'task_type': task_type,
                    'graph_input': json.dumps(None),
                    'config': convert(new_config)
                }
                print("="*50, "part2", "="*50)
                await queue.put(data)
        else:
            order_db = np.array(self.order_list)
            mask = np.array([True] * len(order_db))
            prompt = "请根据用户输入的任务，判断其任务类型"
            while np.sum(mask) > 0 and self.count > 0:
                self.count -= 1
                indices = next(iter(np.where(mask)[0].tolist()))
                mask[indices] = False
                order = order_db[indices].tolist()

                task_names = [seg.strip() for seg in re.split(r"[;；]", order) if seg.strip()]
                for task_name in task_names:
                    task_type_raw = await struct_agent(TaskTypeRouter, prompt, examples).ainvoke({'messages': [("user", task_name)]})

                    if not isinstance(task_type_raw, dict):
                        task_type_raw = json.loads(task_type_raw.model_dump_json())
                    task_type = task_type_raw['task_type']
                    task_id = str(uuid.uuid4())
                    data = {
                        'task_id': task_id,
                        'task_name': task_name,
                        'task_type': task_type,
                        'graph_input': convert({"messages": [("user", task_name)]}),
                        'config': convert({
                            "configurable": {
                                "thread_id": task_id
                            }
                        })
                    }
                    await queue.put(data)

                    await self._redis_client.hset(f"task:{task_id}", mapping=data)  # hash，存储用户状态（可变
                    # await self._redis_client.xadd(f'task_stream', {'status': 'init'})  # stream，流式记录变更事件（不可变

    async def remove_task_after_timeout(self, task):
        try:
            await asyncio.wait_for(task, timeout=self._TIMEOUT)
        except asyncio.TimeoutError:
            print(f"Task {task.get_name()} timed out after {self._TIMEOUT} seconds")
            await self.send_result(task.task_id, {
                "type": "close",
                "task_id": task.task_id,
                "task_name": task.get_name(),
            })
            raise ValueError(f"⏲ {task.get_name()} 超时！")
        finally:
            self._active_workers.discard(task)

    async def gather_tasks(self, tasks):
        try:
            responses = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=self._TIMEOUT)  # 等待所有任务完成
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
        if self._task_ctx.get()['task_type']!='retrieve':
            result = {}
            for r in itertools.chain.from_iterable(result_list):
                result = self.merge_result(result, r)
            return result
        else:
            return 

    def flatten_and_tag(self, result):
        if self._task_ctx.get()['task_type']!='retrieve':
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
        else:
            return

    def downstream(self, d, order):
        task_type = self._task_ctx.get()['task_type']
        ## agent_main
        if task_type=='deploy':
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
        elif task_type=='delete':
            self.send_result(self._task_id, f"\n==== 已删除装备 ====")
            for name, id in zip(d['name'], d['id']):
                self.send_result(self._task_id, f"{name}, {id}")
        
        ## agent_retrieve
        elif task_type=='retrieve':
            task_name, task_id, task_result = self._task_ctx.get()['task_name'], self._task_ctx.get()['task_id'], self._task_ctx.get()['task_result']
            self.send_result(self._task_id, f"\n==== 数据库检索结果 ====")
            self.send_result(self._task_id, f"{task_result}")

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
        self._history_redis_ctx.get().add_message(message)

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
            self.test_agent = test_agent

            self._user_name = None
            self._history = pd.DataFrame(columns=['thread_id', 'task_name', 'task_result'])
            
        def add_history(self, thread_id, task_name, task_result):
            self._history.loc[len(self._history)] = [thread_id, task_name, task_result]
        def update_history(self, thread_id, task_name, task_result):
            self.add_history(thread_id, task_name, task_result)
            self._history.drop_duplicates(subset='thread_id', keep='last', inplace=True)
        def print(self):
            self.test_agent.send_result(self.test_agent._task_id, self._history.to_string(index=False))

    class TaskCollection(metaclass=TaskMeta):  # 元类只是注册了未绑定self的方法，还需手动实现绑定self（未绑定的话直接调用会导致缺少self）
        """各种任务的集合类"""
        
        def __init__(self, test_agent):
            self.test_agent = test_agent

            # 初始化已绑定的方法注册表
            self._method_map = {}
            
            # 将未绑定的方法绑定到当前实例
            for label, method in self._unbound_method_map.items():
                self._method_map[label] = method.__get__(self, type(self))  # 方法是描述符（descriptor），method.__get__(self, type(self)) 等价于lambda *args, **kwargs: method(self, *args, **kwargs)，此时就绑定了self


        @register_method('deploy')
        async def deploy_graph(self, **kwargs):
            graph_input = kwargs.get('graph_input', None)
            graph_name = kwargs.get('graph_name', 'MyGraph')
            config = kwargs.get('config', {
                "configurable": {
                    "thread_id": str(uuid.uuid4())
                }
            })

            state_output = await self.stream_output_graph(self.test_agent.graphs['deploy'], graph_input, config, graph_name)
            result = state_output.get('final_response')

            return result
        
        @register_method('delete')
        async def delete_graph(self, **kwargs):
            graph_input = kwargs.get('graph_input', None)
            graph_name = kwargs.get('graph_name', 'MyGraph')
            config = kwargs.get('config', {
                "configurable": {
                    "thread_id": str(uuid.uuid4())
                }
            })

            state_output = await self.stream_output_graph(self.test_agent.graphs['delete'], graph_input, config, graph_name)
            result = state_output.get('final_response')

            return result
        
        @register_method('retrieve')
        async def retrieve_graph(self, **kwargs):
            graph_input = kwargs.get('graph_input', None)
            graph_name = kwargs.get('graph_name', 'MyGraph')
            config = kwargs.get('config', {
                "configurable": {
                    "thread_id": str(uuid.uuid4())
                }
            })

            state_output = await self.stream_output_graph(self.test_agent.graphs['retrieve'], graph_input, config, graph_name)
            result = state_output.get('final_response')

            return result
        

        async def stream_output_graph(self, graph, graph_input, config, graph_name):
            turn = 0
            previous_time = time.time()
            async for node, state_raw in graph.astream(
                    graph_input,
                    subgraphs=True,
                    stream_mode='debug',
                    config=config
                ):
                    state = state_raw['payload']
                    # fileop.save_any_append(state, f'datasets/{self.test_agent.mode}/{graph_name[:5]}.py')

                    if not state.get('values', {}).get('messages', []):
                        continue

                    await self.test_agent.print_state(config['configurable']['thread_id'], state)

                    turn += 1
                    current_time = time.time()
                    iteration_time = current_time - previous_time
                    await self.test_agent.send_result(config['configurable']['thread_id'], f"==={graph_name}=== 第{turn}次运行\n {node} 耗时: {iteration_time:.8f} 秒")
                    previous_time = current_time

            return state.get('values', {})