import json
import random

from pydantic import BaseModel, Field
from typing import Literal, Annotated
from scripts.convert import convert

class Node(BaseModel):
   nodetype: Annotated[Literal['CommanderNode', 'EquipNode', 'PersonnelNode'], Field(description="if Node has children: CommanderNode\nelse: EquipNode or PersonnelNode")]
   name: str
   position: Annotated[list[float]|Literal['null']|None, Field(description="Position of simentity")]
   children: list['Node']|Literal['null']|None

class Team(BaseModel):
   formations: list[Node]

class DeployInfo(BaseModel):
   red: Annotated[Team|Literal['null']|None, Field(description="Deploy info of red side.")]
   blue: Annotated[Team|Literal['null']|None, Field(description="Deploy info of blue side.")]


input_1 = '''\
蓝军, M110狙击步枪_1, 纬度: 24.904849176, 经度: 121.148869906
蓝军, M110狙击步枪_2, 纬度: 24.904849176, 经度: 121.148974893
蓝军, M110狙击步枪_3, 纬度: 24.904753424, 经度: 121.148869907
蓝军, M110狙击步枪_4, 纬度: 24.904753424, 经度: 121.148974893'''
output_1 = {'red': None, 'blue': {'formations': [{'name': 'M110狙击步枪_1', 'nodetype': 'EquipNode', 'position': [121.148869906, 24.904849176], 'children': None}, {'name': 'M110狙击步枪_2', 'nodetype': 'EquipNode', 'position': [121.148974893, 24.904849176], 'children': None}, {'name': 'M110狙击步枪_3', 'nodetype': 'EquipNode', 'position': [121.148869907, 24.904753424], 'children': None}, {'name': 'M110狙击步枪_4', 'nodetype': 'EquipNode', 'position': [121.148974893, 24.904753424], 'children': None}]}} 

input_2 = '''\
蓝军部署的信息：\n- 实体：RQ-7影子战术无人机\n- 编队：V字形\n- 中心点：民生报社南侧坐标(121.1480011, 24.9071713)\n- 间距：20米\n\n具体配置如下：\n1. RQ-7影子战术无人机，所属阵营：蓝，坐标： [121.1480011, 24.907275541656897]\n2. RQ-7影子战术无人机，所属阵营：蓝，坐标： [121.14810008456881, 24.907119179138174]\n3. RQ-7影子战术无人机，所属阵营：蓝，坐标： [121.1479021154312, 24.907119179138174]'''

output_2 = \
{'red': None, 'blue': {'formations': [{'nodetype': 'CommanderNode', 'name': 'V字形', 'position': [121.1480011, 24.9071713], 'children': [{'nodetype': 'EquipNode', 'name': 'RQ-7影子战术无人机', 'position': [121.1480011, 24.907275541656897], 'children': None}, {'nodetype': 'EquipNode', 'name': 'RQ-7影子战术无人机', 'position': [121.14810008456881, 24.907119179138174], 'children': None}, {'nodetype': 'EquipNode', 'name': 'RQ-7影子战术无人机', 'position': [121.1479021154312, 24.907119179138174], 'children': None}]}]}} 

input_3 = '''\
部署方案: 
1. 兵力实体名称: CM-11勇虎主战坦克, 所属阵营: 红, 坐标: [121.1462562, 24.90364364806954]
2. 兵力实体名称: CM-11勇虎主战坦克, 所属阵营: 红, 坐标: [121.1462562, 24.904004751926088] 

理由: 根据部署规程要求，红军在民权街60巷部署两辆CM-11勇虎主战坦克，编队呈纵队形态，间隔20米，选择的坐标位置满足这一要求。'''

output_3 = \
{'red': {'formations': [{'nodetype': 'CommanderNode', 'name': '红军编队', 'position': None, 'children': [{'nodetype': 'PersonnelNode', 'name': 'CM-11勇虎主战坦克', 'position': [121.1462562, 24.90364364806954], 'children': None}, {'nodetype': 'PersonnelNode', 'name': 'CM-11勇虎主战坦克', 'position': [121.1462562, 24.904004751926088], 'children': None}]}]}, 'blue': None}

examples = [
   {'input': input_1, 'output': convert(output_1)},
   {'input': input_2, 'output': convert(output_2)},
   {'input': input_3, 'output': convert(output_3)},
]
random.shuffle(examples)