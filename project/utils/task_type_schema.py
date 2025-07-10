import random

from scripts.convert import convert
from pydantic import BaseModel
from typing import Literal

class TaskTypeRouter(BaseModel):
    task_type: Literal['delete', 'deploy', 'retrieve']

input_1 = '''删除龙龟附近的所有蓝军99A主战坦克'''
output_1 = {'task_type': 'delete'}

input_2 = '''同时删除红军的一辆M1A1主战坦克'''
output_2 = {'task_type': 'delete'}

input_3 = '''在杨梅分局西侧10米部署红方两架四旋翼无人机'''
output_3 = {'task_type': 'deploy'}

input_4 = '''然后在龙龟西南侧呈正三角队形部署蓝军3辆155mm自行火炮'''
output_4 = {'task_type': 'deploy'}

input_5 = '''我想知道数据库中美军装备有哪些'''
output_5 = {'task_type': 'retrieve'}

input_6 = '''我想知道数据库中雷达有哪些，以及每种装备对应的部署规则'''
output_6 = {'task_type': 'retrieve'}

examples = [
    {'input': input_1, 'output': convert(output_1)},
    {'input': input_2, 'output': convert(output_2)},
    {'input': input_3, 'output': convert(output_3)},
    {'input': input_4, 'output': convert(output_4)},
    {'input': input_5, 'output': convert(output_5)},
    {'input': input_6, 'output': convert(output_6)},
]
random.shuffle(examples)