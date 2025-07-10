import json

from pydantic import BaseModel, Field
from scripts.convert import convert
from typing import Literal, Annotated
from copy import deepcopy

class Node(BaseModel):
   nodetype: Annotated[Literal['CommanderNode', 'EquipNode', 'PersonnelNode'], Field(description="if Node has children: CommanderNode\nelse: EquipNode or PersonnelNode")]
   name: Annotated[str, Field(description='Name of the simentity to be deleted')]
   id: Annotated[str|Literal['null']|None, Field(description='ID of the simentity to be deleted')]
   children: list['Node']|Literal['null']|None

class Team(BaseModel):
   formations: Annotated[list[Node], 'Each Node is a formation or a single entity']

class DeleteInfo(BaseModel):
   red: Annotated[Team|Literal['null']|None, Field(description="Delete info of red side.")]
   blue: Annotated[Team|Literal['null']|None, Field(description="Delete info of blue side.")]

input_1 = {'output': '【编组】\n- name: 红箭10反坦克导弹发射车\n  所属team: red\n  id: FTK_HJ10_BP_C__534CE6B74C0C438792B828A9F4CB6ACA\n'}
output_1 = {'red': {'formations': [{'nodetype': 'EquipNode', 'name': '红箭10反坦克导弹发射车', 'id': 'FTK_HJ10_BP_C__534CE6B74C0C438792B828A9F4CB6ACA', 'children': None}]}, 'blue': None} 
# input_2 = '删除蓝方四旋翼侦察机__6'
# output_2 = DeleteInfos(blue=Team(entities=[Entity(id='四旋翼侦察机__6')]))
# input_3 = '删除红方猛士突击车_2和M1A2主战坦克_5'
# output_3 = DeleteInfos(red=Team(entities=[Entity(id='猛士突击车_2'), Entity(id='M1A2主战坦克_5')]))

examples = [
   {'input': input_1, 'output': convert(output_1)},
#    {'input': input_2, 'output': convert(json.loads(output_2.model_dump_json()))},
#    {'input': input_3, 'output': convert(json.loads(output_3.model_dump_json()))},
]

