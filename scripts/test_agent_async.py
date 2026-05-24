import re
import asyncio
import uuid
import itertools
import geopandas as gpd
import numpy as np
import pandas as pd

from IPython.display import display, Markdown
from scripts.flatten import flatten
from scripts.merge_dict import merge_dict
from scripts.stream_output import stream_output_graph
from scripts.time_travel import get_state_by_config, get_states
from fastapi import Depends

class ConversationContext:
    def __init__(self):
        self.user_name = None
        self.history = pd.DataFrame(columns=['checkpoint_id', 'task_name', 'task_result'])
    def print(self):
        print(self.history.to_string(index=False))

result_saver = ConversationContext()

def downstream(d, order, agent):
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
        print(f"\n==== 已删除装备 ====")
        for name, id in zip(d['name'], d['id']):
            print(name, id)


async def task(graph, graph_input, config):
    task = asyncio.current_task()
    task_name = task.get_name() if task else "unknown"

    if not config:
        config = {
            "configurable": {
                "thread_id": uuid.uuid4()
            }
        }
    state_output = await stream_output_graph(graph, graph_input, config, task_name)
    return (config['configurable']['thread_id'], state_output.get('final_response')[0])

async def test_agent(graph, order_list, merge_result, count=999, agent='agent_main', configs=[]):
    # 更新模式，默认order_list为None
    if configs:
        tasks = []
        task_names = []
        this_task_results = []
        for config in configs:
            task_name = get_state_by_config(graph, config)['values']['messages'][0].content
            task_names.append(task_name)
            tasks.append(asyncio.create_task(task(graph, None, config), name=task_name))
            
        responses = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=240)
        for t, res in zip(tasks, responses):
            task_name = t.get_name()
            if isinstance(res, Exception):
                print(f"[{task_name}] 出错: {res}")
            else:
                print(f"[{task_name}] 成功: {res}")
                this_task_results.append(res[1])
                result_saver.history.loc[len(result_saver.history)] = [str(res[0]), task_name, res[1]]
                result_saver.history.drop_duplicates(subset='checkpoint_id', keep='last', inplace=True)

        responses_tasks = list(itertools.chain.from_iterable(this_task_results))
        result = {}
        for response in responses_tasks:
            result = merge_result(result, response)
        print('\n合并后的result: \n', result)
        teams = []
        if result.get('red') not in ['null', None]:
            teams.append(('红方', result['red']))
        if result.get('blue') not in ['null', None]:
            teams.append(('蓝方', result['blue']))
        try:
            d = {}
            old_len = 0
            for color, team in teams:
                for d_flattened in flatten(team):
                    d = merge_dict(d, d_flattened, color)
                d_team = d.get('team', [])
                d_team.extend([color] * (len(d[next(iter(d))])-old_len))
                d['team'] = d_team
                old_len = len(d[next(iter(d))])
            print('\n展平后的d: \n', d)
            downstream(d, '; '.join(task_names), agent=agent)
        except Exception as e:
            print('\nDownstreamError: ', e, '\n', order, '\n')
            bad_orders.append(order)
            
    # 运行模式
    else:  
        order_db = np.array(order_list)
        mask = np.array([True] * len(order_db))
        bad_orders = []
        while np.sum(mask) > 0 and count > 0:
            count -= 1
            indices = next(iter(np.where(mask)[0].tolist()))
            mask[indices] = False
            order = order_db[indices].tolist()
            this_task_results = []
            try:
                # 设置超时任务
                try:
                    # 使用正则表达式同时按英文和中文分号分隔
                    order_input = [seg.strip() for seg in re.split(r'[;；]', order) if seg.strip()]
                    tasks = []
                    for o in order_input:
                        tasks.append(asyncio.create_task(task(graph, {"messages": [("user", o)]}, configs), name=o))
                    responses = await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=240)
                    for t, res in zip(tasks, responses):
                        task_name = t.get_name()
                        if isinstance(res, Exception):
                            print(f"[{task_name}] 出错: {res}")
                        else:
                            print(f"[{task_name}] 成功: {res}")
                            this_task_results.append(res[1])
                            result_saver.history.loc[len(result_saver.history)] = [str(res[0]), task_name, res[1]]
                            result_saver.history.drop_duplicates(subset='checkpoint_id', keep='last', inplace=True)
                except asyncio.TimeoutError:
                    print("Error: 任务超时", '\n\n', order, '\n\n')
                    continue

                if responses is None:
                    print('\n\nError: 未生成任何结果', '\n\n', order, '\n\n')
                    continue
            except Exception as e:
                if 'NoneType' in str(e):
                    bad_orders.append(order)
                print('\n\nTaskError: ', e, '\n\n', order, '\n\n')
                continue

            responses_tasks = list(itertools.chain.from_iterable(this_task_results))
            result = {}
            for response in responses_tasks:
                result = merge_result(result, response)
            print('\n合并后的result: \n', result)
            teams = []
            if result.get('red') not in ['null', None]:
                teams.append(('红方', result['red']))
            if result.get('blue') not in ['null', None]:
                teams.append(('蓝方', result['blue']))

            try:
                d = {}
                old_len = 0
                for color, team in teams:
                    for d_flattened in flatten(team):
                        d = merge_dict(d, d_flattened, color)
                    d_team = d.get('team', [])
                    d_team.extend([color] * (len(d[next(iter(d))])-old_len))
                    d['team'] = d_team
                    old_len = len(d[next(iter(d))])
                print('\n展平后的d: \n', d)
                downstream(d, order, agent=agent)
            except Exception as e:
                print('\nDownstreamError: ', e, '\n', order, '\n')
                bad_orders.append(order)
                continue
            break


