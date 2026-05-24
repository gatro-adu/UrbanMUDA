import time
import numpy as np
import geopandas as gpd

from concurrent import futures
from scripts.flatten import flatten
from scripts.merge_dict import merge_dict
from scripts.downstream import downstream
from shapely import Point
from IPython.display import display, Markdown

def task(graph, order):
    turn = 0
    old_len = 0
    previous_time = time.time()  # 获取开始时间
    for event in graph.stream(
            {"messages": [("user", order)]}, 
            stream_mode='values',
        ):
        turn = turn+1
        messages = event.get("messages")
        for message in messages[old_len:]:
            message.pretty_print()  # 每次都只展现本轮的消息
        print("----")
        old_len = len(messages)

        current_time = time.time()  # 记录当前时间
        iteration_time = current_time - previous_time  # 计算本轮迭代的时间
        print(f"第{turn}次运行, 耗时: {iteration_time:.8f} 秒")
        previous_time = current_time  # 更新上一次迭代的时间
    return event.get('final_response')

def test_agent(graph, order_list, count=999, agent='agent_main'):
    order_db = np.array(order_list)
    mask = np.array([True]*len(order_db))
    # 测试用循环次数
    bad_orders = []
    while sum(mask)>0 and count>0:
        count-=1
        # indices = random.sample((np.where(mask)[0]).tolist(), 1)  # 随机选择一条指令（可以多个）
        indices = next(iter(np.where(mask)[0].tolist()))  # 顺序选择一条指令（可以多个）
        mask[indices] = False
        order = order_db[indices].tolist()
        # continue
        try:
            with futures.ThreadPoolExecutor() as executor:
                # 提交任务并获取Future对象
                try:
                    future = executor.submit(task, graph, order)
                    # future = executor.submit(task, "Deploy 4x mobile command centers of the Red Army in a square formation around the center of Herald Square.")
                    # 设置超时时间为4分钟
                    response = future.result(timeout=240)
                except futures.TimeoutError:
                    print("Error: 任务超时", '\n\n', order, '\n\n')
                    continue
            if response is None:
                print('\n\nError: 未生成任何结果', '\n\n', order, '\n\n')
                continue
        except Exception as e: 
            if 'NoneType' in str(e):
                bad_orders.append(order)
            print('\n\nError: ', e, '\n\n', order, '\n\n')
            continue
        teams = []
        if response['red']!='null' and response['red']!=None:
            color_str = '红方'
            teams.append((color_str, response['red']))
        if response['blue']!='null' and response['blue']!=None:
            color_str = '蓝方'
            teams.append((color_str, response['blue']))
        try:
            d={}
            for color, team in teams:
                for d_extracted in flatten(team):
                    d = merge_dict(d, d_extracted, color)
            d['team'] = [color]*len(d[next(iter(d))])
            downstream(d, order, agent=agent)
        except Exception as e:
            print('\n\nError: ', e, '\n\nerror-orders: ', order, '\n\n')
            bad_orders.append(order)
            continue
