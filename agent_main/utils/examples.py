from langchain_core.documents import Document

from agent_main.utils.schema import Plans, Plan, Entity
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

input_colorunknown_1 = '''CM-21步兵战车6辆部署在杨梅区杨梅国小附近，并以矩形队形展开'''

output_colorunknown_1 = Plans(plans=[Plan(color='unknown', entities=[Entity(name='CM-21步兵战车1', steps='选择杨梅国小的坐标121.1435883, 24.9060153，作为第一个战车的部署点，紧邻学校，适合进行前线部署。', coordinates=[121.1435883, 24.9060153]), Entity(name='CM-21步兵战车2', steps='选择杨梅国小附近的坐标121.1435883, 24.9059873，作为第二个战车的部署点，确保战车的防御性和可机动性。', coordinates=[121.1435883, 24.9059873]), Entity(name='CM-21步兵战车3', steps='选择杨梅国小向西的集乳站坐标121.14401, 24.9060153，作为第三个战车的部署点，形成横向展开的矩形阵型。', coordinates=[121.14401, 24.9060153]), Entity(name='CM-21步兵战车4', steps='选择杨梅国小附近的集乳站坐标121.1442134, 24.9057596，作为第四个战车的部署点，继续矩形展开。', coordinates=[121.1442134, 24.9057596]), Entity(name='CM-21步兵战车5', steps='选择杨梅国小南侧的坐标121.1434156, 24.9060153，作为第五个战车的部署点，形成纵深防御。', coordinates=[121.1434156, 24.9060153]), Entity(name='CM-21步兵战车6', steps='选择杨梅国小南侧的坐标121.1434156, 24.9059873，作为第六个战车的部署点，确保整个阵型形成矩形。', coordinates=[121.1434156, 24.9059873])])])


input_distance_1 = '''在杨梅公交站南侧50米，配置红军3门120mm迫榴炮，要求间隔80米，前后距离30米'''

# 此处后期可以加上预思考，预先思考选择哪个点作为起始部署点
output_distance_1 = Plans(plans=[Plan(color='red', entities=[Entity(name='120mm迫榴炮1', steps='存在两个杨梅公交站，坐标分别(121.1450721, 24.9069268)、(121.1448669, 24.9066573)，由于其中前者南侧存在道路不便于坦克部署，因此选择杨梅公交站(121.1448669, 24.9066573)。然后根据部署指令，向南移动50米得到第一个炮的位置，坐标(121.1448669, 24.9066573-0.0005)，即(121.1448669, 24.9061573)。', coordinates=[121.1448669, 24.9061573]), Entity(name='120mm迫榴炮2', steps='从第一个炮的位置向东80米和南30米移动得到第二个炮的位置，坐标(121.1448669+0.0008, 24.9061573-0.0003)，即(121.1456669, 24.9058573)。', coordinates=[121.1456669, 24.9058573]), Entity(name='120mm迫榴炮3', steps='从第一个炮的位置向西80米和南30米移动得到第三个炮的位置，坐标(121.1448669-0.0008, 24.9066573-0.0003)，即(121.1440669, 24.9063573)。', coordinates=[121.1440669, 24.9063573])])])

input_tri_1 = '''在集乳站和杨梅国小站之间呈正三角队形部署三辆坦克'''

output_tri_1 = Plan(color='unknown', entities=[Entity(name='坦克1', steps='选择杨梅国小站坐标(121.1435883, 24.9060153)作为正三角形的顶点，部署第一辆坦克，确保能在建筑物附近得到较高的观察和防御地点。', coordinates=[121.1435883, 24.9060153]), Entity(name='坦克2', steps='选择集乳站坐标(121.14401, 24.9058174)作为正三角形的一个底角进行部署，确保与第一辆坦克形成正三角形的边。', coordinates=[121.14401, 24.9058174]), Entity(name='坦克3', steps='确定在杨梅国小与集乳站之间，进行三角形展开所需的第三个位置：首先计算两点之间的中点坐标((121.1435883+121.14401)/2, (24.9060153+24.9058174)/2)，即(121.1437991, 24.90591635)，然后在中点垂直方向，选择(121.1439991, 24.90611635)作为第三辆坦克的部署点，形成正三角形结构。', coordinates=[121.1439991, 24.90611635])])

input_yi_1 = '''在集乳站的东侧呈一字队形部署蓝军三门火炮，要求间隔40米'''

output_yi_1 = Plans(plans=[Plan(color='blue', entities=[Entity(name='火炮1', steps='选择集乳站的坐标(121.14401, 24.9058174)作为第一个火炮的部署点，按照部署指令东侧展开。', coordinates=[121.14401, 24.9058174]), Entity(name='火炮2', steps='选择集乳站东侧40米的位置，计算获得新坐标(121.14401+0.0004, 24.9058174)，即(121.14441, 24.9058174)作为第二个火炮的部署点。', coordinates=[121.14441, 24.9058174]), Entity(name='火炮3', steps='选择集乳站东侧80米的位置，计算获得新坐标(121.14401+0.0008, 24.9058174)，即(121.14481, 24.9058174)作为第三个火炮的部署点。', coordinates=[121.14481, 24.9058174])])])

examples_messages = [  # 不包含提取属性的例子
    {"input": input_colorunknown_1, "output": output_colorunknown_1},
    {"input": input_distance_1, "output": output_distance_1},
    # {"input": input_tri_1, "output": output_tri_1},
    {"input": input_yi_1, "output": output_yi_1},
]

# toolcall_examples = [
#     HumanMessage(content='在集乳站的东侧20米处，呈正三角队形部署红军三辆坦克，要求两两间隔60米; 在中山路和杨梅陆桥交叉口呈矩形队形部署蓝军4架无人机，两两间隔15米', additional_kwargs={}, response_metadata={}, id='d69926f3-7d19-477b-b52c-b5b504f246b6'),
#     AIMessage(content='', additional_kwargs={'tool_calls': [{'id': 'chatcmpl-tu5ombQoHTDDMeoqVK5IdzMJw66KI', 'function': {'arguments': '{"azimuth": 90, "d": 20, "x": 121.14401, "y": 24.9058174}', 'name': 'point_tool'}, 'type': 'function'}, {'id': 'chatcmpl-tu5ombQoHTDDMeoqVK5IdzMJw66KI', 'function': {'arguments': '{"azimuth": 0, "d": 15, "x": 121.143536, "y": 24.9064239}', 'name': 'point_tool'}, 'type': 'function'}], 'refusal': None}, response_metadata={'token_usage': {'completion_tokens': 84, 'prompt_tokens': 4646, 'total_tokens': 4730, 'completion_tokens_details': {'accepted_prediction_tokens': 0, 'audio_tokens': 0, 'reasoning_tokens': 0, 'rejected_prediction_tokens': 0}, 'prompt_tokens_details': {'audio_tokens': 0, 'cached_tokens': 0}}, 'model_name': 'gpt-4o-mini', 'system_fingerprint': 'fp_b705f0c291', 'finish_reason': 'tool_calls', 'logprobs': None}, name='generate_plan', id='run-4c8577e9-00e9-4173-a89a-e1fa7d2ad11d-0', tool_calls=[{'name': 'point_tool', 'args': {'azimuth': 90, 'd': 20, 'x': 121.14401, 'y': 24.9058174}, 'id': 'chatcmpl-tu5ombQoHTDDMeoqVK5IdzMJw66KI', 'type': 'tool_call'}, {'name': 'point_tool', 'args': {'azimuth': 0, 'd': 15, 'x': 121.143536, 'y': 24.9064239}, 'id': 'chatcmpl-tu5ombQoHTDDMeoqVK5IdzMJw66KI', 'type': 'tool_call'}], usage_metadata={'input_tokens': 4646, 'output_tokens': 84, 'total_tokens': 4730, 'input_token_details': {'audio': 0, 'cache_read': 0}, 'output_token_details': {'audio': 0, 'reasoning': 0}}),
#     ToolMessage(content='[121.14420796706065, 24.905817399868642];\n[121.143536, 24.90655931389779]', name='tool_node', id='9c10d0b4-bcdb-46ee-9631-83cdc4022c62', tool_call_id='chatcmpl-tu5ombQoHTDDMeoqVK5IdzMJw66KI'),
#     AIMessage(content='', additional_kwargs={'tool_calls': [{'id': 'chatcmpl-AbJf7JHSDaDRCRSOsxDb65BtIYvsd', 'function': {'arguments': '{"d": 60, "n": 3, "x": 121.14420796706065, "y": 24.905817399868642}', 'name': 'formation_tool'}, 'type': 'function'}, {'id': 'chatcmpl-AbJf7JHSDaDRCRSOsxDb65BtIYvsd', 'function': {'arguments': '{"d": 15, "n": 4, "x": 121.143536, "y": 24.9064239}', 'name': 'formation_tool'}, 'type': 'function'}], 'refusal': None}, response_metadata={'token_usage': {'completion_tokens': 89, 'prompt_tokens': 4815, 'total_tokens': 4904, 'completion_tokens_details': {'accepted_prediction_tokens': 0, 'audio_tokens': 0, 'reasoning_tokens': 0, 'rejected_prediction_tokens': 0}, 'prompt_tokens_details': {'audio_tokens': 0, 'cached_tokens': 0}}, 'model_name': 'gpt-4o-mini', 'system_fingerprint': 'fp_b705f0c291', 'finish_reason': 'tool_calls', 'logprobs': None}, name='generate_plan', id='run-2d15c986-e719-4f45-95d1-605bca766d5f-0', tool_calls=[{'name': 'formation_tool', 'args': {'d': 60, 'n': 3, 'x': 121.14420796706065, 'y': 24.905817399868642}, 'id': 'chatcmpl-AbJf7JHSDaDRCRSOsxDb65BtIYvsd', 'type': 'tool_call'}, {'name': 'formation_tool', 'args': {'d': 15, 'n': 4, 'x': 121.143536, 'y': 24.9064239}, 'id': 'chatcmpl-AbJf7JHSDaDRCRSOsxDb65BtIYvsd', 'type': 'tool_call'}], usage_metadata={'input_tokens': 4815, 'output_tokens': 89, 'total_tokens': 4904, 'input_token_details': {'audio': 0, 'cache_read': 0}, 'output_token_details': {'audio': 0, 'reasoning': 0}}),
#     ToolMessage(content='[[121.14420796706065, 24.906130124891714], [121.14450491727746, 24.90566103705663], [121.14391101684384, 24.90566103705663]];\n[[121.143536, 24.906519652085645], [121.14364098840144, 24.906423899963052], [121.143536, 24.906328147913122], [121.14343101159855, 24.906423899963052]]', name='tool_node', id='2b4697a7-f624-4a0a-885f-f5fbc1b56364', tool_call_id='chatcmpl-AbJf7JHSDaDRCRSOsxDb65BtIYvsd'),
#     AIMessage(content='', additional_kwargs={'tool_calls': [{'id': 'chatcmpl-fGZdOuC4aNHvf4GUgooNpWJgU8SGv', 'function': {'arguments': '{"plans":[{"color":"red","entities":[{"coordinates":[121.14420796706065,24.906130124891714],"name":"红军坦克1","steps":"在集乳站东侧20米处，呈正三角队形部署红军三辆坦克，要求两两间隔60米。"},{"coordinates":[121.14450491727746,24.90566103705663],"name":"红军坦克2","steps":"在集乳站东侧20米处，呈正三角队形部署红军三辆坦克，要求两两间隔60米。"},{"coordinates":[121.14391101684384,24.90566103705663],"name":"红军坦克3","steps":"在集乳站东侧20米处，呈正三角队形部署红军三辆坦克，要求两两间隔60米。"}]},{"color":"blue","entities":[{"coordinates":[121.143536,24.906519652085645],"name":"蓝军无人机1","steps":"在中山路和杨梅陆桥交叉口呈矩形队形部署蓝军4架无人机，两两间隔15米。"},{"coordinates":[121.14364098840144,24.906423899963052],"name":"蓝军无人机2","steps":"在中山路和杨梅陆桥交叉口呈矩形队形部署蓝军4架无人机，两两间隔15米。"},{"coordinates":[121.143536,24.906328147913122],"name":"蓝军无人机3","steps":"在中山路和杨梅陆桥交叉口呈矩形队形部署蓝军4架无人机，两两间隔15米。"},{"coordinates":[121.14343101159855,24.906423899963052],"name":"蓝军无人机4","steps":"在中山路和杨梅陆桥交叉口呈矩形队形部署蓝军4架无人机，两两间隔15米。"}]}]}', 'name': 'Plans'}, 'type': 'function'}], 'refusal': None}, response_metadata={'token_usage': {'completion_tokens': 448, 'prompt_tokens': 5165, 'total_tokens': 5613, 'completion_tokens_details': {'accepted_prediction_tokens': 0, 'audio_tokens': 0, 'reasoning_tokens': 0, 'rejected_prediction_tokens': 0}, 'prompt_tokens_details': {'audio_tokens': 0, 'cached_tokens': 0}}, 'model_name': 'gpt-4o-mini', 'system_fingerprint': 'fp_b705f0c291', 'finish_reason': 'tool_calls', 'logprobs': None}, name='generate_plan', id='run-47e4fc50-6f86-43f4-afe7-aff218d220d1-0', tool_calls=[{'name': 'Plans', 'args': {'plans': [{'color': 'red', 'entities': [{'coordinates': [121.14420796706065, 24.906130124891714], 'name': '红军坦克1', 'steps': '在集乳站东侧20米处，呈正三角队形部署红军三辆坦克，要求两两间隔60米。'}, {'coordinates': [121.14450491727746, 24.90566103705663], 'name': '红军坦克2', 'steps': '在集乳站东侧20米处，呈正三角队形部署红军三辆坦克，要求两两间隔60米。'}, {'coordinates': [121.14391101684384, 24.90566103705663], 'name': '红军坦克3', 'steps': '在集乳站东侧20米处，呈正三角队形部署红军三辆坦克，要求两两间隔60米。'}]}, {'color': 'blue', 'entities': [{'coordinates': [121.143536, 24.906519652085645], 'name': '蓝军无人机1', 'steps': '在中山路和杨梅陆桥交叉口呈矩形队形部署蓝军4架无人机，两两间隔15米。'}, {'coordinates': [121.14364098840144, 24.906423899963052], 'name': '蓝军无人机2', 'steps': '在中山路和杨梅陆桥交叉口呈矩形队形部署蓝军4架无人机，两两间隔15米。'}, {'coordinates': [121.143536, 24.906328147913122], 'name': '蓝军无人机3', 'steps': '在中山路和杨梅陆桥交叉口呈矩形队形部署蓝军4架无人机，两两间隔15米。'}, {'coordinates': [121.14343101159855, 24.906423899963052], 'name': '蓝军无人机4', 'steps': '在中山路和杨梅陆桥交叉口呈矩形队形部署蓝军4架无人机，两两间隔15米。'}]}]}, 'id': 'chatcmpl-fGZdOuC4aNHvf4GUgooNpWJgU8SGv', 'type': 'tool_call'}], usage_metadata={'input_tokens': 5165, 'output_tokens': 448, 'total_tokens': 5613, 'input_token_details': {'audio': 0, 'cache_read': 0}, 'output_token_details': {'audio': 0, 'reasoning': 0}}),
#     ToolMessage(content="Final Plans: {'plans': [{'color': 'red', 'entities': [{'coordinates': [121.14420796706065, 24.906130124891714], 'name': '红军坦克1', 'steps': '在集乳站东侧20米处，呈正三角队形部署红军三辆坦克，要求两两间隔60米。'}, {'coordinates': [121.14450491727746, 24.90566103705663], 'name': '红军坦克2', 'steps': '在集乳站东侧20米处，呈正三角队形部署红军三辆坦克，要求两两间隔60米。'}, {'coordinates': [121.14391101684384, 24.90566103705663], 'name': '红军坦克3', 'steps': '在集乳站东侧20米处，呈正三角队形部署红军三辆坦克，要求两两间隔60米。'}]}, {'color': 'blue', 'entities': [{'coordinates': [121.143536, 24.906519652085645], 'name': '蓝军无人机1', 'steps': '在中山路和杨梅陆桥交叉口呈矩形队形部署蓝军4架无人机，两两间隔15米。'}, {'coordinates': [121.14364098840144, 24.906423899963052], 'name': '蓝军无人机2', 'steps': '在中山路和杨梅陆桥交叉口呈矩形队形部署蓝军4架无人机，两两间隔15米。'}, {'coordinates': [121.143536, 24.906328147913122], 'name': '蓝军无人机3', 'steps': '在中山路和杨梅陆桥交叉口呈矩形队形部署蓝军4架无人机，两两间隔15米。'}, {'coordinates': [121.14343101159855, 24.906423899963052], 'name': '蓝军无人机4', 'steps': '在中山路和杨梅陆桥交叉口呈矩形队形部署蓝军4架无人机，两两间隔15米。'}]}]}.", name='to Plans', id='53bd2961-e482-4bab-8dda-573d4f1fc05c', tool_call_id='chatcmpl-fGZdOuC4aNHvf4GUgooNpWJgU8SGv')]


toolcall_examples = [HumanMessage(content='在集乳站的东侧20米处，呈正三角队形部署红军三辆坦克，要求两两间隔60米; 在中山路和杨梅陆桥交叉口呈矩形队形部署蓝军4架无人机，两两间隔15米', name='user'),
AIMessage(content='我将分步骤完成这个部署任务：\n\n1. 首先确定红军坦克和蓝军无人机的部署中心点。\n我需要先找到集乳站的坐标，然后向东偏移20米作为第一个编组部署中心点。\n以及中山路和杨梅陆桥交叉口的坐标作为第二个编组部署中心点。\n\n集乳站坐标：(121.14401, 24.9058174)\n\n中山路和杨梅陆桥交叉口坐标：(121.1438768, 24.9063685)', name='generate_plan', tool_calls=[{'name': 'point_tool', 'args': {'x': 121.14401, 'y': 24.9058174, 'azimuth': 90, 'd': 20}, 'id': '11'}]),
ToolMessage(content='[121.14420796706065, 24.905817399868642]', name='tool_node', tool_call_id='11'),
ToolMessage(content='[121.1438768, 24.9063685]', name='tool_node', tool_call_id='12'),
AIMessage(content='2. 接下来计算红军三角队形和蓝军矩形队形：', name='generate_plan', tool_calls=[{'name': 'formation_tool', 'args': {'x': 121.14420796706065, 'y': 24.905817399868642, 'n': 3, 'd': 60}, 'id': '21'}, {'name': 'formation_tool', 'args': {'x': 121.1438768, 'y': 24.9063685, 'n': 4, 'd': 15}, 'id': '22'}]),
ToolMessage(content='[[121.14420796706065, 24.906130124891714], [121.14450491727746, 24.90566103705663], [121.14391101684384, 24.90566103705663]]', name='tool_node', tool_call_id='21'),
ToolMessage(content='[[121.1438768, 24.90646425208636], [121.14398178835458, 24.906368499963047], [121.1438768, 24.90627274791241], [121.14377181164542, 24.906368499963047]]', name='tool_node', tool_call_id='22'),
AIMessage(content='3. 生成最终部署计划：', name='generate_plan', tool_calls=[{'name': 'Plans', 'args': {'plans': [{'color': 'red', 'entities': [{'name': '坦克1', 'coordinates': [121.14420796706065, 24.906130124891714], 'steps': '以三角队形部署在集乳站东侧20米处'}, {'name': '坦克2', 'coordinates': [121.14450491727746, 24.90566103705663], 'steps': '以三角队形部署在集乳站东侧20米处'}, {'name': '坦克3', 'coordinates': [121.14391101684384, 24.90566103705663], 'steps': '以三角队形部署在集乳站东侧20米处'}]}, {'color': 'blue', 'entities': [{'name': '无人机1', 'coordinates': [121.1438768, 24.90646425208636], 'steps': '以矩形队形部署在中山路和杨梅陆桥交叉口'}, {'name': '无人机2', 'coordinates': [121.14398178835458, 24.906368499963047], 'steps': '以矩形队形部署在中山路和杨梅陆桥交叉口'}, {'name': '无人机3', 'coordinates': [121.1438768, 24.90627274791241], 'steps': '以矩形队形部署在中山路和杨梅陆桥交叉口'}, {'name': '无人机4', 'coordinates': [121.14377181164542, 24.906368499963047], 'steps': '以矩形队形部署在中山路和杨梅陆桥交叉口'}]}]}, 'id': '4'}]),
ToolMessage(content="Final Plans: {'plans': [{'color': 'red', 'entities': [{'name': '坦克1', 'coordinates': [121.14420796706065, 24.906130124891714], 'steps': '以三角队形部署在集乳站东侧20米处'}, {'name': '坦克2', 'coordinates': [121.14450491727746, 24.90566103705663], 'steps': '以三角队形部署在集乳站东侧20米处'}, {'name': '坦克3', 'coordinates': [121.14391101684384, 24.90566103705663], 'steps': '以三角队形部署在集乳站东侧20米处'}]}, {'color': 'blue', 'entities': [{'name': '无人机1', 'coordinates': [121.1438768, 24.90646425208636], 'steps': '以矩形队形部署在中山路和杨梅陆桥交叉口'}, {'name': '无人机2', 'coordinates': [121.14398178835458, 24.906368499963047], 'steps': '以矩形队形部署在中山路和杨梅陆桥交叉口'}, {'name': '无人机3', 'coordinates': [121.1438768, 24.90627274791241], 'steps': '以矩形队形部署在中山路和杨梅陆桥交叉口'}, {'name': '无人机4', 'coordinates': [121.14377181164542, 24.906368499963047], 'steps': '以矩形队形部署在中山路和杨梅陆桥交叉口'}]}]}.", name='to Plans', tool_call_id='4')]

think_example = '''
部署指令：在杨梅公交站南侧30米，配置红军3门120mm迫榴炮，要求间隔20米，呈正三角队形; 在集乳站和杨梅国小站之间呈三角队形部署三辆坦克

思考：根据你的指令，我们需要完成以下两个部署任务：

1. 在杨梅公交站南侧30米，配置红军3门120mm迫榴炮，要求间隔20米，呈正三角队形。
2. 在集乳站和杨梅国小站之间呈三角队形部署三辆坦克。

### 第一步：确定杨梅公交站的位置

首先，我们需要找到杨梅公交站的坐标。由于地图中有两个名为“杨梅”的公交站，我们需要选择一个合适的站点。根据默认规则，我们应该选择一个站点，使得部署对象（迫榴炮）不会被部署在道路上。让我们检查两个站点附近是否有道路。

#### 杨梅公交站1: (121.1450721, 24.9069268)
- 位于中山路上，不适合部署迫榴炮。

#### 杨梅公交站2: (121.1448669, 24.9066573)
- 位于非主干道，适合部署迫榴炮。

因此，我们将选择杨梅公交站2作为部署点。

### 第二步：计算迫榴炮的部署位置

我们需要在杨梅公交站2南侧30米处，部署3门120mm迫榴炮，呈正三角队形，间隔20米。为此，我们需要计算出这个三角队形的顶点坐标。

#### 计算杨梅公交站2南侧30米的位置
使用 `point_tool` 调用，以杨梅公交站2的坐标为起点，方位角为180度（正南方向），距离为30米。

#### 计算三角队形的顶点坐标
使用 `polygon_formation_tool` 调用，以计算好的杨梅公交站2南侧30米位置为中心点，部署3门迫榴炮，间隔20米，形成正三角队形。

### 第三步：确定集乳站和杨梅国小站的位置

接下来，我们需要找到集乳站和杨梅国小站的坐标，以便确定它们之间的中间位置作为坦克的部署中心点。

#### 集乳站坐标：(121.14401, 24.9058174)
#### 杨梅国小站坐标：(121.1434156, 24.9059873)

#### 计算两站之间的中点
使用 `midpoint_tool` 调用，计算这两站之间的中点坐标。

### 第四步：计算坦克的部署位置

在计算出的中点位置，部署三辆坦克，呈正三角队形，间隔20米。

#### 计算三角队形的顶点坐标
使用 `polygon_formation_tool` 调用，以计算好的中点位置为中心点，部署3辆坦克，间隔20米，形成正三角队形。

### 调用工具并生成最终部署计划

现在我们已经明确了所有必要的坐标和队形信息，接下来调用相应的工具来计算具体的坐标，并生成最终的部署计划。'''