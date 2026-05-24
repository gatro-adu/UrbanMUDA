# from scripts.workflow_react import react_agent
from agent_main.utils.schema import DeployInfo, examples
from agent_main.utils.tools import (
    polygon_formation_tool, line_formation_tool, midpoint_tool, point_tool, midpoint_tool, azimuth_tool, polygon_centroid_tool, linestring_centroid_tool, distance_tool, name_nearby_tool, pos_nearby_tool, circle_formation_tool, v_formation_tool, find_intersection_tool, think_tool
)
from agent_main.utils.rules import default, tool, think

# # <工具规则>{tool}</工具规则>
rules = f'''\
<默认规则>{default}</默认规则>
<思考规则>{think}</思考规则>'''

prompt = f'''\
你是一个兵力部署专家但数学计算能力不强。你的任务是遵循兵力部署指令将兵力配置在地图上，请一步步思考。
最后使用structure输出合理的兵力配置，包括每个兵力实体的名称、所属阵营（红或蓝）、坐标。请务必涵盖用户输入中的所有编组或兵力实体。
你需要注意的规则如下：
{rules}'''

# formation_tools = [polygon_formation_tool, line_formation_tool, circle_formation_tool, v_formation_tool]
# centroid_tools = [polygon_centroid_tool, linestring_centroid_tool]
# base_tools = [distance_tool, azimuth_tool, midpoint_tool, point_tool, find_intersection_tool]
# nearby_tools = [name_nearby_tool, pos_nearby_tool]

# tools = base_tools + nearby_tools + formation_tools + centroid_tools

# graph = react_agent(tools=tools, response_format=DeployInfo, examples=examples, prompt=prompt)


# 使用mcp
from langchain_mcp_adapters.client import MultiServerMCPClient
# from agent_locate.utils.schema import merge_delete_infos_json
from scripts.workflow_react_async import react_agent
# from datasets.input_data.data.zh_inputs_unique_2 import orders as orders_raw
from langchain_core.runnables import RunnableConfig


import json
import asyncio
from functools import partial
from pydantic import BaseModel, Field
from typing_extensions import Annotated
from langgraph.prebuilt import ToolNode
from langgraph.graph import MessagesState, StateGraph, END
from langgraph.types import Command
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import ToolMessage, AIMessage
from langchain.tools import StructuredTool
# from scripts.llm_load import llm_gpt4omini as llm
# from scripts.llm_load import llm_qwen as llm
from scripts.llm_load import llm_main as llm
from scripts.llm_load import llm_finetune
from scripts.workflow_struct import struct_agent

def create_react_agent(tools, system_prompt, response_format, history_messages=[], output_examples=[], llm=llm, memory=True):
    class structure(BaseModel):
        '''Tool to get structured output'''
        output: Annotated[str, Field(description='Output to be structured')]

    class AgentState(MessagesState):
        final_response: list
    
    async def call_model(state: AgentState):
        template = ChatPromptTemplate([
            ('system', system_prompt),
            *history_messages,
            ("placeholder", "{messages}")
        ])
        # print('-'*100)
        # print(template)
        real_tools = tools+[structure]
        llm_with_tools = template | llm.bind_tools(real_tools)
        response = await llm_with_tools.ainvoke({'messages': state['messages']})

        tool_call_names = [tc.get('name', '') for tc in response.tool_calls]

        if not response.tool_calls:
            # update={"messages": [{'role': 'user', 'content': 'Output your answer using "structure" tool when no tools are needed!'}]}
            # goto = 'agent'
                ## 直接将原始信息＋Output的 user消息一块加入messages
            update={"messages": [
                {'role': 'assistant', 'content': response.content},
                {'role': 'user', 'content': 'Output your answer using "structure" tool when no tools are needed!'}
            ]}
            goto = 'agent'

        elif len(set(tool_call_names))==1 and tool_call_names[0]=='structure':
            update = {"messages": [response]}
            goto = 'respond'
        else:
            for tc in response.tool_calls[:]:
                if tc['name']=='structure':
                    response.tool_calls.remove(tc)
            update={"messages": [response]}
            goto = 'tools'

        return Command(
            update=update,
            goto=goto
        )

    async def respond(state: AgentState):
        responses = []  # [json1, json2,...]
        tool_messages = []
        for tool_call in state['messages'][-1].tool_calls:
            response = await struct_agent(response_format, examples=output_examples).ainvoke({'messages': [('user', tool_call['args']['output'])]})
            print('\n===Unstructured Output===\n', tool_call['args']['output'])
            if not isinstance(response, dict):
                response = json.loads(response.model_dump_json())
            print('\n===Structured Output==\n', response, '\n')
            responses.append(response)
            tool_messages.append(ToolMessage(content=response, tool_call_id=tool_call['id']))
        return Command(
            update={'final_response': responses, 'messages': tool_messages},
            goto=END
        )

    workflow = StateGraph(AgentState)
    workflow.add_node('agent', call_model)\
            .add_node('respond', respond)\
            .add_node('tools', ToolNode(tools))\
            .set_entry_point('agent')\
            .add_edge('tools', 'agent')\

    if memory:
        checkpointer = InMemorySaver()
        agent = workflow.compile(checkpointer=checkpointer)
    else: agent = workflow.compile()
    return agent


async def make_graph(memory: bool):
    client = MultiServerMCPClient({
        "main": {
            "command": "uv",
            "args": ["run", "-m", "mcp_server.main_server"],
            "transport": "stdio",
        },
        # "locate": {
        #     "command": "python",
        #     "args": ["mcp/locate_server.py"],
        #     "transport": "stdio",
        # },
        # "main": {
        #     "url": "http://localhost:8999/mcp",
        #     "transport": "streamable_http",
        # }
    })
    tools = await client.get_tools()
    graph_mcp = create_react_agent(tools, prompt, DeployInfo, output_examples=examples, memory=memory)

    return graph_mcp

from mcp_server.main_server import get_nearby_geoentities_no_dingliang, get_nearby_geoentities_no_dingxing, get_nearby_geoentities_no_compress
async def make_graph_no_dingxing(memory: bool):
    client = MultiServerMCPClient({
        "main": {
            "command": "uv",
            "args": ["run", "-m", "mcp_server.main_server"],
            "transport": "stdio",
        },
    })
    tools = await client.get_tools()
    # get_nearby_geoentities_partial = partial(get_nearby_geoentities, if_no_dingxing=True)
    for i, tool in enumerate(tools):
        if tool.name == 'get_nearby_geoentities':
            tools[i] = StructuredTool.from_function(
                func=get_nearby_geoentities_no_dingxing,
            )
    # print(tools)
    graph_mcp = create_react_agent(tools, prompt, DeployInfo, output_examples=examples, memory=memory)
    return graph_mcp
async def make_graph_no_dingliang(memory: bool):
    client = MultiServerMCPClient({
        "main": {
            "command": "uv",
            "args": ["run", "-m", "mcp_server.main_server"],
            "transport": "stdio",
        },
    })
    tools = await client.get_tools()
    for i, tool in enumerate(tools):
        if tool.name == 'get_nearby_geoentities':
            tools[i] = StructuredTool.from_function(get_nearby_geoentities_no_dingliang)
    graph_mcp = create_react_agent(tools, prompt, DeployInfo, output_examples=examples, memory=memory)
    return graph_mcp
async def make_graph_no_compress(memory: bool):
    client = MultiServerMCPClient({
        "main": {
            "command": "uv",
            "args": ["run", "-m", "mcp_server.main_server"],
            "transport": "stdio",
        },
    })
    tools = await client.get_tools()
    for i, tool in enumerate(tools):
        if tool.name == 'get_nearby_geoentities':
            tools[i] = StructuredTool.from_function(get_nearby_geoentities_no_compress)
    graph_mcp = create_react_agent(tools, prompt, DeployInfo, output_examples=examples, memory=memory)
    return graph_mcp
async def make_graph_no_reflection(memory: bool):
    client = MultiServerMCPClient({
        "main": {
            "command": "uv",
            "args": ["run", "-m", "mcp_server.main_server"],
            "transport": "stdio",
        },
    })
    tools = await client.get_tools()
    think = '''\
任务一: 在指定区域内配置用户指定编组（用户已指定队形）
步骤：
    1. 使用"get_deploy_rules"获取目标配置兵力实体的部署规则，明确部署约束条件。
    2. 使用"get_nearby_geoentities"获取目标区域内及周边的地理实体信息，用于辅助判断可部署区域与可用地理特征（如树林、建筑、沟壑等）。
    3. 根据地理实体和规则，使用相关工具（如几何计算工具）确定编组中心点。
    4. 用户已指定队形，请优先使用"get_formation"，根据中心点和队形信息，一次性获取该编组内所有兵力实体的位置。
    5. 使用"structure"输出完整的部署方案。

任务二: 在指定区域内配置用户指定编组（用户未指定队形）
步骤：
    1. 使用"get_deploy_rules"获取目标配置兵力实体的部署规则，明确部署约束条件。
    2. 使用"get_nearby_geoentities"获取目标区域内及周边的地理实体信息，用于辅助判断可部署区域与可用地理特征（如树林、建筑、沟壑等）。
    3. 根据地理实体和规则，使用相关工具（如几何计算工具）确定编组中心点。
    4. 根据任务内容与环境特点，从以下支持的队形库中自主选择最合适的队形。
        - 正多边形队形（如三角形、方形、五边形）
        - 直线队形（如横队、纵队）
    5. 使用"get_formation"，根据中心点和队形信息，一次性获取该编组内所有兵力实体的位置。
    6. 使用"structure"输出完整的部署方案。
    
任务三：在指定区域内配置零散兵力实体（不按照正常编组进行部署）
步骤：
    1. 使用"get_deploy_rules"获取零散兵力实体的部署规则，明确部署约束条件。
    2. 使用"get_nearby_geoentities"获取目标区域内及周边的地理实体信息，用于辅助判断可部署区域与可用地理特征（如树林、建筑、沟壑等）。
    3. 结合部署规则与地理实体，使用相关工具（如几何计算工具）识别多个适合单兵部署的小规模区域。
    4. 对每个兵力实体，逐个确定部署位置：
        - 优先选择满足遮蔽/隐蔽、地形适应性强的位置。
        - 保证部署间距、分布合理，避免集中。
        - 若任务目标涉及警戒、封锁、伏击等作战需求，可根据功能角色进行位置微调（如前置哨兵、中段火力点、后方掩护）。
    5. 使用 structure 输出所有零散兵力实体的最终部署方案。
    
注意：
- 如果存在多个编组，可以多次调用工具，以便推理更高效。
- 优先使用"get_formation"简化部署过程，提高效率和一致性。
- 自主选择队形时，请考虑兵力数量、地形限制、部署规则等。
- 不允许在有成熟计算工具支持的情况下手动计算点坐标。
- 不允许将兵力实体配置在同一坐标下。
- 每次调用工具前请先查看对应的工具规则，确保工具的正确使用。'''
    rules = f'''\
<默认规则>{default}</默认规则>
<思考规则>{think}</思考规则>'''
    prompt = f'''\
你是一个兵力部署专家但数学计算能力不强。你的任务是遵循兵力部署指令将兵力配置在地图上，请一步步思考。
最后使用structure输出合理的兵力配置，包括每个兵力实体的名称、所属阵营（红或蓝）、坐标。请务必涵盖用户输入中的所有编组或兵力实体。
你需要注意的规则如下：
{rules}'''
    graph_mcp = create_react_agent(tools, prompt, DeployInfo, output_examples=examples, memory=memory)
    return graph_mcp
async def make_graph_no_finetune(memory: bool):
    client = MultiServerMCPClient({
        "main": {
            "command": "uv",
            "args": ["run", "-m", "mcp_server.main_server"],
            "transport": "stdio",
        },
    })
    tools = await client.get_tools()
    graph_mcp = create_react_agent(tools, prompt, DeployInfo, output_examples=examples, memory=memory)
    return graph_mcp

async def make_graph_finetune(memory: bool):
    client = MultiServerMCPClient({
        "main": {
            "command": "uv",
            "args": ["run", "-m", "mcp_server.main_server"],
            "transport": "stdio",
        },
    })
    tools = await client.get_tools()
    graph_mcp = create_react_agent(tools, prompt, DeployInfo, output_examples=examples, memory=memory, llm=llm_finetune)
    return graph_mcp
async def make_graph_zeroshot(memory: bool):
    client = MultiServerMCPClient({
        "main": {
            "command": "uv",
            "args": ["run", "-m", "mcp_server.main_server"],
            "transport": "stdio",
        },
    })
    tools = await client.get_tools()
    prompt = f'''\
你是一个兵力部署专家但数学计算能力不强。你的任务是遵循兵力部署指令将兵力配置在地图上，请一步步思考。
最后使用structure输出合理的兵力配置，包括每个兵力实体的名称、所属阵营（红或蓝）、坐标。请务必涵盖用户输入中的所有编组或兵力实体。'''
    graph_mcp = create_react_agent(tools, prompt, DeployInfo, output_examples=examples, memory=memory)
    return graph_mcp


async def make_graph_fewshot(memory: bool):
    client = MultiServerMCPClient({
        "main": {
            "command": "uv",
            "args": ["run", "-m", "mcp_server.main_server"],
            "transport": "stdio",
        },
    })
    tools = await client.get_tools()
    prompt = f'''\
你是一个兵力部署专家但数学计算能力不强。你的任务是遵循兵力部署指令将兵力配置在地图上，请一步步思考。
最后使用structure输出合理的兵力配置，包括每个兵力实体的名称、所属阵营（红或蓝）、坐标。请务必涵盖用户输入中的所有编组或兵力实体。'''
    history_messages = [
        {"role": "user", "content": "红军在观音圣像西北侧20米处部署4个99A式坦克，要求呈正方形队形，两两间隔50米"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "call_1", "type": "function", "function": {"name": "get_deploy_rules", "arguments": {"name": "99A式坦克"}}}]},
        {"role": "tool", "tool_call_id": "call_1", "content": "=== 99A式坦克有如下部署规则 ===\n以下是针对99A式坦克的三条部署规则：\n\n1. **严密阵型分布**：在战斗部署时，99A式坦克应形成以“V”字形或线性阵型，以增强整体火力覆盖和相互支援能力。每辆坦克之间要保持适当的距离，确保在遭遇敌方火力时，能够迅速调整阵型并保持战斗力。\n\n2. **地形适应部署**：在部署时，要根据战场地形进行灵活调整。99A式坦克在丘陵、森林或城市环境中尽量利用自然掩护，避免暴露在敌方视线范围内。确保在高地或有利位置上进行观察和打击，充分发挥其火力优势。\n\n3. **快速机动与支援配合**：在战斗中，99A式坦克应与步兵和其他支援单位紧密配合，确保有效的火力支援与机动防御。坦克在进攻时应适时进行机动，避免陷入固定战斗，随时准备调整位置以应对敌方动作变化。\n\n这些规则旨在最大限度地增加99A式坦克的战斗效能，并提高整体作战成功率。"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "call_2", "type": "function", "function": {"name": "get_nearby_geoentities", "arguments": {"loc_name": "观音圣像"}}}]},
        {"role": "tool", "tool_call_id": "call_2", "content": "=== 找到观音圣像附近地理实体 ===\n\n({'name': '观音圣像', 'tag': 'common-building', 'geometry': 'POLYGON ((121.1489839 24.9047093, 121.1490056 24.9046949, 121.1490047 24.9046715, 121.1489811 24.9046619, 121.148958 24.904676, 121.1489592 24.9046977, 121.1489839 24.9047093))'}, {'rcc': 'Disconnected (DC)', 'distance': 27.997913736723397, 'azimuth': 136.34608229700225}, {'tag': 'steps', 'geometry': 'LINESTRING (121.14920477318407 24.904472292731093, 121.14919149999999 24.9044854)', 'bearing': '207.05805406772052'})\n({'name': '观音圣像', 'tag': 'common-building', 'geometry': 'POLYGON ((121.1489839 24.9047093, 121.1490056 24.9046949, 121.1490047 24.9046715, 121.1489811 24.9046619, 121.148958 24.904676, 121.1489592 24.9046977, 121.1489839 24.9047093))'}, {'rcc': 'Disconnected (DC)', 'distance': 27.58076418386372, 'azimuth': 144.8383306189847}, {'name': '杨梅狮子亭', 'tag': 'shelter', 'geometry': 'POLYGON ((121.1491368 24.904432999999997, 121.1491379 24.904443599999997, 121.1491426 24.904453399999998, 121.14915030000002 24.904461399999995, 121.1491604 24.9044669, 121.14917190000001 24.904469299999995, 121.14918360000001 24.904468499999993, 121.14919450000001 24.904464300000004, 121.14919456493156 24.90446424965981, 121.14917752896466 24.904451858563284, 121.14915224474869 24.90443702100592, 121.14913747892308 24.904430175680034, 121.1491368 24.904432999999997))'})\n({'name': '观音圣像', 'tag': 'common-building', 'geometry': 'POLYGON ((121.1489839 24.9047093, 121.1490056 24.9046949, 121.1490047 24.9046715, 121.1489811 24.9046619, 121.148958 24.904676, 121.1489592 24.9046977, 121.1489839 24.9047093))'}, {'rcc': 'Disconnected (DC)', 'distance': 22.797787185733444, 'azimuth': 137.6744301186617}, {'tag': 'footway', 'geometry': 'LINESTRING (121.14919149999999 24.9044854, 121.149146 24.904511499999998)', 'bearing': '196.52658783994588'})\n({'name': '观音圣像', 'tag': 'common-building', 'geometry': 'POLYGON ((121.1489839 24.9047093, 121.1490056 24.9046949, 121.1490047 24.9046715, 121.1489811 24.9046619, 121.148958 24.904676, 121.1489592 24.9046977, 121.1489839 24.9047093))'}, {'rcc': 'Disconnected (DC)', 'distance': 12.112448455020463, 'azimuth': -174.91881769989854}, {'tag': 'shelter', 'geometry': 'POLYGON ((121.1489815 24.9044998, 121.14893500000001 24.9045396, 121.1489521 24.904555999999996, 121.14899859999998 24.904516199999996, 121.1489815 24.9044998))'})\n({'name': '观音圣像', 'tag': 'common-building', 'geometry': 'POLYGON ((121.1489839 24.9047093, 121.1490056 24.9046949, 121.1490047 24.9046715, 121.1489811 24.9046619, 121.148958 24.904676, 121.1489592 24.9046977, 121.1489839 24.9047093))'}, {'rcc': 'Disconnected (DC)', 'distance': 3.0901146089957443, 'azimuth': 136.0976122150059}, {'tag': 'footway', 'geometry': 'LINESTRING (121.14891840000001 24.904858299999994, 121.148863 24.904849300000002, 121.14884709999998 24.904829400000004, 121.14884100000002 24.904796999999995, 121.14884860000001 24.904751599999997, 121.1488919 24.904692399999988, 121.1489617 24.9046057, 121.1490337 24.904534899999998, 121.14906180000001 24.904517699999996, 121.1491104 24.904508, 121.149146 24.904511499999998, 121.1491369 24.9045417, 121.1491096 24.9045919, 121.1490738 24.9046444, 121.1490383 24.904696600000005, 121.14900570000002 24.9047619, 121.148992 24.904790099999996, 121.1489708 24.9048369, 121.14895029999998 24.904851399999995, 121.14891840000001 24.904858299999994)', 'bearing': '0.0'})\n({'name': '观音圣像', 'tag': 'common-building', 'geometry': 'POLYGON ((121.1489839 24.9047093, 121.1490056 24.9046949, 121.1490047 24.9046715, 121.1489811 24.9046619, 121.148958 24.904676, 121.1489592 24.9046977, 121.1489839 24.9047093))'}, {'rcc': 'Disconnected (DC)', 'distance': 5.854077658407226, 'azimuth': -32.404411899048114}, {'name': '龙龟', 'tag': 'common-building', 'geometry': 'POLYGON ((121.14895290000001 24.904755899999998, 121.1489234 24.9047396, 121.14889289999999 24.904785, 121.1489224 24.904801299999995, 121.14895290000001 24.904755899999998))'})\n({'name': '观音圣像', 'tag': 'common-building', 'geometry': 'POLYGON ((121.1489839 24.9047093, 121.1490056 24.9046949, 121.1490047 24.9046715, 121.1489811 24.9046619, 121.148958 24.904676, 121.1489592 24.9046977, 121.1489839 24.9047093))'}, {'rcc': 'Disconnected (DC)', 'distance': 18.501272288215386, 'azimuth': -39.182163033899045}, {'tag': 'footway', 'geometry': 'LINESTRING (121.14882579999998 24.904867299999996, 121.14884709999998 24.904829400000004)', 'bearing': '42.62611395547435'})\n({'name': '观音圣像', 'tag': 'common-building', 'geometry': 'POLYGON ((121.1489839 24.9047093, 121.1490056 24.9046949, 121.1490047 24.9046715, 121.1489811 24.9046619, 121.148958 24.904676, 121.1489592 24.9046977, 121.1489839 24.9047093))'}, {'rcc': 'Disconnected (DC)', 'distance': 23.161886628239525, 'azimuth': -35.89539675601659}, {'tag': 'steps', 'geometry': 'LINESTRING (121.1488061 24.90492219999999, 121.14882579999998 24.904867299999996)', 'bearing': '55.25029610803048'})\n({'name': '观音圣像', 'tag': 'common-building', 'geometry': 'POLYGON ((121.1489839 24.9047093, 121.1490056 24.9046949, 121.1490047 24.9046715, 121.1489811 24.9046619, 121.148958 24.904676, 121.1489592 24.9046977, 121.1489839 24.9047093))'}, {'rcc': 'Disconnected (DC)', 'distance': 29.337802798836577, 'azimuth': -33.80258878210506}, {'tag': 'footway', 'geometry': 'LINESTRING (121.1488061 24.90492219999999, 121.14880566030794 24.904928675464774)', 'bearing': '262.5215203808873'})\n({'name': '观音圣像', 'tag': 'common-building', 'geometry': 'POLYGON ((121.1489839 24.9047093, 121.1490056 24.9046949, 121.1490047 24.9046715, 121.1489811 24.9046619, 121.148958 24.904676, 121.1489592 24.9046977, 121.1489839 24.9047093))'}, {'rcc': 'Partially Overlapping (PO)', 'distance': 0.0, 'azimuth': -76.18342007946093}, {'name': '观音圣像', 'tag': 'common-building', 'geometry': 'POLYGON ((121.1490056 24.9046949, 121.1490047 24.904671499999996, 121.14898110000001 24.904661899999997, 121.148958 24.904675999999995, 121.1489592 24.904697699999996, 121.1489839 24.904709299999997, 121.1490056 24.9046949))'})\n({'name': '观音圣像', 'tag': 'common-building', 'geometry': 'POLYGON ((121.1489839 24.9047093, 121.1490056 24.9046949, 121.1490047 24.9046715, 121.1489811 24.9046619, 121.148958 24.904676, 121.1489592 24.9046977, 121.1489839 24.9047093))'}, {'rcc': 'Disconnected (DC)', 'distance': 14.221409887967486, 'azimuth': -3.7689893585651193}, {'tag': 'footway', 'geometry': 'LINESTRING (121.1489674 24.904895000000003, 121.1489708 24.9048369)', 'bearing': '83.54541959784176'})\n({'name': '观音圣像', 'tag': 'common-building', 'geometry': 'POLYGON ((121.1489839 24.9047093, 121.1490056 24.9046949, 121.1490047 24.9046715, 121.1489811 24.9046619, 121.148958 24.904676, 121.1489592 24.9046977, 121.1489839 24.9047093))'}, {'rcc': 'Disconnected (DC)', 'distance': 20.674248569773184, 'azimuth': -4.7196241508384595}, {'name': '贵客步道', 'tag': 'steps', 'geometry': 'LINESTRING (121.1489537 24.904952799999993, 121.1489674 24.904895000000003)', 'bearing': '65.3815402152795'})\n({'name': '观音圣像', 'tag': 'common-building', 'geometry': 'POLYGON ((121.1489839 24.9047093, 121.1490056 24.9046949, 121.1490047 24.9046715, 121.1489811 24.9046619, 121.148958 24.904676, 121.1489592 24.9046977, 121.1489839 24.9047093))'}, {'rcc': 'Disconnected (DC)', 'distance': 27.192943546865795, 'azimuth': -6.383250256339431}, {'name': '贵客步道', 'tag': 'footway', 'geometry': 'LINESTRING (121.1489537 24.904952799999993, 121.14894205020963 24.904976639869133)', 'bearing': '226.6283328585152'})"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "call_3", "type": "function", "function": {"name": "get_new_point", "arguments": {"coord": [121.14899475, 24.9046856], "azimuth": -150, "d": 20}}}]},
        {"role": "tool", "tool_call_id": "call_3", "content": "从[121.14899475, 24.9046856]出发的方位角-150方向距离20米处的坐标为: [121.14889576749721, 24.904529237426985]"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "call_4", "type": "function", "function": {"name": "get_formation", "arguments": {"coord": [121.14889576749721, 24.904529237426985], "desc": "4个99A式坦克呈正方形队形，两两间隔50米。以中心点为中心，四个坦克分别位于正方形的四个顶点：西北角、东北角、东南角、西南角。正方形边长为50米，对角线长约70.71米。坦克编号为1-4号。"}}}]},
        {"role": "tool", "tool_call_id": "call_4", "content": "符合\"4个99A式坦克呈正方形队形，两两间隔50米。以中心点为中心，四个坦克分别位于正方形的四个顶点：西北角、东北角、东南角、西南角。正方形边长为50米，对角线长约70.71米。坦克编号为1-4号。中心点/领队在[121.14889576749721, 24.904529237426985]\"的队形为: ['坦克位置坐标：\\n1号坦克: [121.14889576749721, 24.904848411122096] (西北角)\\n2号坦克: [121.1492457234919, 24.90452923701652] (东北角)\\n3号坦克: [121.14889576749721, 24.904210063718224] (东南角)\\n4号坦克: [121.14854581150252, 24.90452923701652] (西南角)']"},
        {"role": "assistant", "content": "", "tool_calls": [{"id": "call_5", "type": "function", "function": {"name": "structure", "arguments": {"output": "红军在观音圣像西北侧20米处部署4个99A式坦克的兵力配置方案：\n\n**部署理由：**\n1. 根据用户指令，在观音圣像西北侧20米处部署4个99A式坦克，呈正方形队形，两两间隔50米\n2. 首先获取了观音圣像的地理位置信息，计算其中心点作为参考\n3. 从观音圣像中心点向西北方向（方位角-150度）移动20米，确定编组中心点\n4. 使用正方形队形，以编组中心点为中心，四个坦克分别位于正方形的四个顶点\n5. 正方形边长为50米，确保两两间隔50米的要求\n\n**兵力配置详情：**\n\n1. **1号99A式坦克**\n   - 所属阵营：红\n   - 坐标：[121.14889576749721, 24.904848411122096]\n   - 位置：正方形西北角\n\n2. **2号99A式坦克**\n   - 所属阵营：红\n   - 坐标：[121.1492457234919, 24.90452923701652]\n   - 位置：正方形东北角\n\n3. **3号99A式坦克**\n   - 所属阵营：红\n   - 坐标：[121.14889576749721, 24.904210063718224]\n   - 位置：正方形东南角\n\n4. **4号99A式坦克**\n   - 所属阵营：红\n   - 坐标：[121.14854581150252, 24.90452923701652]\n   - 位置：正方形西南角\n\n**队形特点：**\n- 正方形队形，边长50米，对角线约70.71米\n- 编组中心点位于观音圣像西北侧20米处\n- 四个坦克相互支援，形成360度火力覆盖\n- 符合99A式坦克的部署规则，特别是严密阵型分布要求\n\n**部署验证：**\n- 所有坦克均位于观音圣像西北侧区域\n- 相邻坦克间距50米，对角线间距约70.71米\n- 无重复坐标，每个坦克有独立位置\n- 队形对称，便于指挥和协同作战"}}}]},
        {"role": "tool", "tool_call_id": "call_5", "content": "{'red': {'formations': [{'nodetype': 'CommanderNode', 'name': '正方形队形', 'position': None, 'children': [{'nodetype': 'EquipNode', 'name': '99A式坦克_1', 'position': [121.14889576749721, 24.904848411122096], 'children': None}, {'nodetype': 'EquipNode', 'name': '99A式坦克_2', 'position': [121.1492457234919, 24.90452923701652], 'children': None}, {'nodetype': 'EquipNode', 'name': '99A式坦克_3', 'position': [121.14889576749721, 24.904210063718224], 'children': None}, {'nodetype': 'EquipNode', 'name': '99A式坦克_4', 'position': [121.14854581150252, 24.90452923701652], 'children': None}]}]}, 'blue': None}"}
    ]
    history_messages_new = []
    for m in history_messages:
        if m['role']=='assistant':
            if tool_calls := m.get("tool_calls", []):
                tool_calls[0]['function']['arguments'] = json.dumps(tool_calls[0]['function']['arguments'])
                history_messages_new.append(
                    AIMessage(
                        content=m.get("content", ""),
                        additional_kwargs={
                            "tool_calls": tool_calls
                        }
                    )
                )
            else:
                history_messages_new.append(
                    AIMessage(
                        content=m.get("content", ""),
                    )
                )
        elif m['role']=='tool':
            history_messages_new.append(
                ToolMessage(
                    content=m["content"],
                    tool_call_id=m["tool_call_id"]
                )
            )
        else:
            history_messages_new.append(m)
    graph_mcp = create_react_agent(tools, prompt, DeployInfo, output_examples=examples, memory=memory, history_messages=history_messages_new)
    return graph_mcp

# graph_mcp = react_agent(prompt, DeployInfo, examples, memory=False)

if __name__ == '__main__':
    # uv run -m agent_main.agent

    graph = asyncio.run(make_graph_no_dingxing(False))
    # asyncio.run(graph.ainvoke({'messages': [{'role':'user', 'content': '你好'}]}, {'configuable': {'thread_id': 'good'}}))


# [
#     StructuredTool(
#         name='get_nearby_geoentities', 
#         description='Tool to obtain nearby geoentities using location name', 
#         args_schema={
#             'properties': {
#                 'loc_name': {'description': 'Name of the location', 'title': 'Loc Name', 'type': 'string'}
#             }, 
#             'required': ['loc_name'], 
#             'title': 'get_nearby_geoentitiesArguments', 
#             'type': 'object'
#         }, 
#         response_format='content_and_artifact', 
#         coroutine=<function convert_mcp_tool_to_langchain_tool.<locals>.call_tool at 0x73c4c0abe700>), 
#     StructuredTool(name='get_deploy_rules', description='Tool to get deployment rules of simentity using its name', args_schema={'properties': {'name': {'description': 'Name of the simentity', 'title': 'Name', 'type': 'string'}}, 'required': ['name'], 'title': 'get_deploy_rulesArguments', 'type': 'object'}, response_format='content_and_artifact', coroutine=<function convert_mcp_tool_to_langchain_tool.<locals>.call_tool at 0x73c4f6d26a20>), 
#     StructuredTool(name='get_new_point', description='Tool that calculates the new point based on the current point', args_schema={'properties': {'coord': {'description': 'Coordinates of current point', 'examples': [[[114.31, 30.57], [114.32, 30.57]]], 'items': {'type': 'number'}, 'title': 'Coord', 'type': 'array'}, 'azimuth': {'anyOf': [{'type': 'number'}, {'type': 'integer'}], 'description': 'Azimuth to current point, in degree', 'examples': [90, 180], 'title': 'Azimuth'}, 'd': {'anyOf': [{'type': 'number'}, {'type': 'integer'}], 'description': 'Distance to current point, in meters', 'examples': [10, 20], 'title': 'D'}}, 'required': ['coord', 'azimuth', 'd'], 'title': 'get_new_pointArguments', 'type': 'object'}, metadata={'title': None, 'readOnlyHint': None, 'destructiveHint': None, 'idempotentHint': True, 'openWorldHint': None}, response_format='content_and_artifact', coroutine=<function convert_mcp_tool_to_langchain_tool.<locals>.call_tool at 0x73c4c0b33ec0>), StructuredTool(name='get_formation', description='Tool to get coordinates of simentities in formation based on the formation name', args_schema={'properties': {'coord': {'description': 'Coordinates of central/leader point of formation', 'items': {'type': 'number'}, 'title': 'Coord', 'type': 'array'}, 'desc': {'description': '具体队形描述，包括位置坐标、排列方式、装备配置等必要且完备的元素', 'title': 'Desc', 'type': 'string'}}, 'required': ['coord', 'desc'], 'title': 'get_formationArguments', 'type': 'object'}, response_format='content_and_artifact', coroutine=<function convert_mcp_tool_to_langchain_tool.<locals>.call_tool at 0x73c4c0b402c0>)
# ]