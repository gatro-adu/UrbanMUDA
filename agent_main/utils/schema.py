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
{'red': None, 'blue': {'formations': [{'nodetype': 'CommanderNode', 'name': 'V字形', 'position': [121.1480011, 24.9071713], 'children': [{'nodetype': 'EquipNode', 'name': 'RQ-7影子战术无人机_1', 'position': [121.1480011, 24.907275541656897], 'children': None}, {'nodetype': 'EquipNode', 'name': 'RQ-7影子战术无人机_2', 'position': [121.14810008456881, 24.907119179138174], 'children': None}, {'nodetype': 'EquipNode', 'name': 'RQ-7影子战术无人机_3', 'position': [121.1479021154312, 24.907119179138174], 'children': None}]}]}} 

input_3 = '''\
部署方案: 
1. 兵力实体名称: CM-11勇虎主战坦克, 所属阵营: 红, 坐标: [121.1462562, 24.90364364806954]
2. 兵力实体名称: CM-11勇虎主战坦克, 所属阵营: 红, 坐标: [121.1462562, 24.904004751926088] 

理由: 根据部署规程要求，红军在民权街60巷部署两辆CM-11勇虎主战坦克，编队呈纵队形态，间隔20米，选择的坐标位置满足这一要求。'''

output_3 = \
{'red': {'formations': [{'nodetype': 'CommanderNode', 'name': '红军编队', 'position': None, 'children': [{'nodetype': 'EquipNode', 'name': 'CM-11勇虎主战坦克_1', 'position': [121.1462562, 24.90364364806954], 'children': None}, {'nodetype': 'EquipNode', 'name': 'CM-11勇虎主战坦克_2', 'position': [121.1462562, 24.904004751926088], 'children': None}]}]}, 'blue': None}

input_4 = '''\
=== 红军部署方案 ===\n根据部署规则和地理实体信息，将3个军官-狙击枪（男）部署在大成路西南侧20米处，呈正三角队形，两两间隔20米。以下是各兵力实体的坐标：\n\n1. 军官-狙击枪（男）1: [121.1457291, 24.90698004166103]\n2. 军官-狙击枪（男）2: [121.14582808433306, 24.906823679136107]\n3. 军官-狙击枪（男）3: [121.14563011566693, 24.906823679136107]\n\n以上部署方案满足以下条件：\n\n- 队形为正三角形，符合用户要求。\n- 两两间隔20米，确保了兵力分布的合理性和战术灵活性。\n- 所有兵力实体均部署在大成路西南侧20米范围内的地理实体附近，符合地理特征限制。\n- 每个兵力实体的位置都考虑了地形与隐蔽性，避免了集中部署的风险。'''
output_4 = \
{'red': {'formations': [{'nodetype': 'CommanderNode', 'name': '正三角队形', 'position': None, 'children': [{'nodetype': 'PersonnelNode', 'name': '军官-狙击枪（男）_1', 'position': [121.1457291, 24.90698004166103], 'children': None}, {'nodetype': 'PersonnelNode', 'name': '军官-狙击枪（男）_2', 'position': [121.14582808433306, 24.906823679136107], 'children': None}, {'nodetype': 'PersonnelNode', 'name': '军官-狙击枪（男）_3', 'position': [121.14563011566693, 24.906823679136107], 'children': None}]}]}, 'blue': None}

input_5 = '''\
士兵_反无人武器（台）编组部署方案如下：

### **部署区域和队形**
- **中心点坐标**：民权街西南侧的中心点坐标为 [121.145691, 24.9036897]。
- **队形类型**：正五边形队形，两两间距40米。

### **兵力实体部署位置**
根据正五边形队形计算，以下为5个士兵_反无人武器（台）的具体坐标：

1. 士兵1：[121.145691, 24.90399687328669]
2. 士兵2：[121.14601131218559, 24.903784621423284]
3. 士兵3：[121.14588896326985, 24.903441191450256]
4. 士兵4：[121.14549303673014, 24.903441191450256]
5. 士兵5：[121.1453706878144, 24.903784621423284]

### **部署理由**
1. **符合用户指令**：用户明确要求在民权街西南侧部署5个士兵_反无人武器（台），并呈正五边形队形，两两间隔40米，因此我调用`get_formation`工具来确保队形符合用户要求。
2. **地理位置分析**：通过`get_nearby_geoentities`获取民权街西南侧的地理实体信息，确保队形位于民权街的西南侧。
3. **队形合理性**：正五边形队形适用于均衡覆盖和隐蔽部署，每个实体之间间隔40米，符合用户要求。
4. **避免集中部署**：通过正五边形的分布方式，确保五个士兵_反无人武器在地理分布上均衡且合理，避免集中在一个区域。

以上部署方案基于用户指令和地理分析，确保了队形和部署位置的准确性。'''

output_5 = \
{'red': {'formations': [{'nodetype': 'CommanderNode', 'name': '正五边形队形', 'position': [121.145691, 24.9036897], 'children': [{'nodetype': 'PersonnelNode', 'name': '士兵_反无人武器（台）_1', 'position': [121.145691, 24.90399687328669], 'children': None}, {'nodetype': 'PersonnelNode', 'name': '士兵_反无人武器（台）_2', 'position': [121.14601131218559, 24.903784621423284], 'children': None}, {'nodetype': 'PersonnelNode', 'name': '士兵_反无人武器（台）_3', 'position': [121.14588896326985, 24.903441191450256], 'children': None}, {'nodetype': 'PersonnelNode', 'name': '士兵_反无人武器（台）_4', 'position': [121.14549303673014, 24.903441191450256], 'children': None}, {'nodetype': 'PersonnelNode', 'name': '士兵_反无人武器（台）_5', 'position': [121.1453706878144, 24.903784621423284], 'children': None}]}]}, 'blue': None}

input_6 = '''\
=== 狙击手_4部署方案 ===

1. **编组名称**：男狙击手_4
   **所属阵营**：蓝军
   **部署数量**：2
   **中心点坐标**：新日元中药行东侧20米处
   **队形**：横队
   **队形间距**：50米

2. **各个兵力实体坐标**：
   - [121.1450257760689, 24.90739169917896]
   - [121.1460156239311, 24.90739169917896]'''

output_6 = \
{'red': None, 'blue': {'formations': [{'nodetype': 'CommanderNode', 'name': '横队', 'position': None, 'children': [{'nodetype': 'PersonnelNode', 'name': '男狙击手_4_1', 'position': [121.1450257760689, 24.90739169917896], 'children': None}, {'nodetype': 'PersonnelNode', 'name': '男狙击手_4_2', 'position': [121.1460156239311, 24.90739169917896], 'children': None}]}]}}

examples = [
   {'input': input_1, 'output': convert(output_1)},
   {'input': input_2, 'output': convert(output_2)},
   {'input': input_3, 'output': convert(output_3)},
   {'input': input_4, 'output': convert(output_4)},
   {'input': input_5, 'output': convert(output_5)},
   {'input': input_6, 'output': convert(output_6)},
]
random.shuffle(examples)