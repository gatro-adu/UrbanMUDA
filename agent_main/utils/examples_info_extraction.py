from pydantic import BaseModel, Field
from typing import Literal, Annotated, Optional

class Entity(BaseModel):
    name: Annotated[str, Field(description='目标配置的实体名称')]
    quantity: Annotated[int|None, Field(None, description='目标配置的实体个数')]

class Formation(BaseModel):
    formation_name: Annotated[str, Field(description='目标配置的队形名称')]
    addon: Annotated[str, Field(None, description='队形附加描述')]

class Location(BaseModel):
    reference: str = Field(description="参照物，例如：杨梅国小、杨梅公交站、高地A")
    direction: str|None = Field(None, description='相对方向，例如：北侧、南侧、西北方向')
    distance: float|None = Field(None, description="距离数值，例如：50、2，单位为米")
    terrain: str|None = Field(None, description="地形属性，例如：高地、山坡、公路附近")

class Team(BaseModel):
    """提取结构化的兵力部署信息"""

    team_color: Annotated[Literal['red', 'blue'], Field(description='目标配置的阵营')]
    unit: Annotated[str|None, Field(None, description='提取执行部署任务的单位名称')]
    entities: Annotated[list[Entity], Field(description='目标配置的所有实体')]
    location: Annotated[Location, Field(description='目标配置的区域名称')]
    formation: Annotated[Formation|None, Field(None, description='目标配置的队形信息')]

input_colorunknown_1 = '''CM-21步兵战车6辆部署在杨梅国小附近'''
output_colorunknown_1 = Team(team_color='red', entities=[Entity(name='CM-21步兵战车', quantity=6)], location=Location(reference='杨梅国小'))
# output_colorunknown_1 = Team(team_color='red', entities=[Entity(name='CM-21步兵战车', quantity=6)], location='杨梅国小')

input_distance_1 = '''在杨梅公交站南侧50米，配置红军4门120mm迫榴炮'''
output_distance_1 = Team(team_color='red', entities=[Entity(name='120mm迫榴炮', quantity=4)], location=Location(reference='杨梅公交站', direction='南侧', distance=50))

input_tri_1 = '''在集乳站和杨梅国小站之间呈正三角队形部署蓝军三辆M1A2主战坦克，要求两两间隔30米'''
output_tri_1 = Team(team_color='blue', entities=[Entity(name='M1A2主战坦克', quantity=3)], location=Location(reference='集乳站和杨梅国小站之间'), formation=Formation(formation_name='正三角', addon='两两间隔30米'))


fewshot = [
    (input_colorunknown_1, output_colorunknown_1.model_dump()),
    (input_distance_1, output_distance_1.model_dump()),
    (input_tri_1, output_tri_1.model_dump()),
]

'''{
    'team_color': {
        'description': '目标配置的阵营', 
        'enum': ['red', 'blue'], 
        'title': 'Team Color', 
        'type': 'string'
    }, 
    'unit': {
        'anyOf': [{'type': 'string'}, {'type': 'null'}], 
        'default': None, 
        'description': '提取执行部署任务的单位名称', 
        'title': 'Unit'
    }, 
    'entities': {
        'description': '目标配置的所有实体', 
        'items': {
            'properties': {
                'name': {
                    'description': '目标配置的实体名称', 
                    'title': 'Name', 
                    'type': 'string'
                }, 
                'quantity': {
                    'description': '目标配置的实体个数', 
                    'title': 'Quantity', 
                    'type': 'integer'
                }
            }, 
        'required': ['name', 'quantity'], 
        'title': 'Entity', 'type': 'object'
        }, 
        'title': 'Entities', 
        'type': 'array'
    }, 
    'location': {
        'description': '目标配置的区域名称', 
        'title': 'Location', 'type': 'string'
    }, 
    'formation': {
        'anyOf': [
            {
                'properties': {
                    'formation_name': {
                        'description': '目标配置的队形名称', 
                        'title': 'Formation Name', 
                        'type': 'string'
                    }, 
                    'addon': {
                        'anyOf': [{'type': 'string'}, {'type': 'null'}], 
                        'default': None, 
                        'description': '队形附加描述', 
                        'title': 'Addon'
                    }
                }, 
                'required': ['formation_name'], 
                'title': 'Formation', 
                'type': 'object'
            }, 
            {'type': 'null'}
        ], 
        'default': None, 
        'description': '目标配置的队形信息'
    }
}'''