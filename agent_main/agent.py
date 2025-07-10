from scripts.workflow_react import react_agent
from agent_main.utils.schema import DeployInfo, examples
from agent_main.utils.tools import (
    polygon_formation_tool, line_formation_tool, midpoint_tool, point_tool, midpoint_tool, azimuth_tool, polygon_centroid_tool, linestring_centroid_tool, distance_tool, name_nearby_tool, pos_nearby_tool, circle_formation_tool, v_formation_tool, find_intersection_tool, think_tool
)
from agent_main.utils.rules import default, tool, think

# <工具规则>{tool}</工具规则>
rules = f'''\
<默认规则>{default}</默认规则>
<思考规则>{think}</思考规则>'''

prompt = f'''\
你是一个兵力部署专家但数学计算能力不强。你的任务是遵循兵力部署指令将兵力配置在地图上，请一步步思考。
最后使用structure输出合理的兵力配置，包括每个兵力实体的名称、所属阵营（红或蓝）、坐标。请务必涵盖用户输入中的所有编组或兵力实体。
你需要注意的规则如下：
{rules}'''

formation_tools = [polygon_formation_tool, line_formation_tool, circle_formation_tool, v_formation_tool]
centroid_tools = [polygon_centroid_tool, linestring_centroid_tool]
base_tools = [distance_tool, azimuth_tool, midpoint_tool, point_tool, find_intersection_tool]
nearby_tools = [name_nearby_tool, pos_nearby_tool]

tools = base_tools + nearby_tools + formation_tools + centroid_tools

graph = react_agent(tools=tools, response_format=DeployInfo, examples=examples, prompt=prompt)


# 使用mcp
from langchain_mcp_adapters.client import MultiServerMCPClient
# from agent_locate.utils.schema import merge_delete_infos_json
from scripts.workflow_react_async import react_agent
# from datasets.input_data.data.zh_inputs_unique_2 import orders as orders_raw
from langchain_core.runnables import RunnableConfig

async def make_graph(memory: bool):
    client = MultiServerMCPClient({
        "main": {
            "command": "python",
            "args": ["mcp/main_server.py"],
            "transport": "stdio",
        },
        # "locate": {
        #     "command": "python",
        #     "args": ["mcp/locate_server.py"],
        #     "transport": "stdio",
        # },
        # "main": {
        #     "url": "http://localhost:8000/mcp",
        #     "transport": "streamable_http",
        # }
    })
    tools = await client.get_tools()
    graph_mcp = react_agent(tools, prompt, DeployInfo, examples, memory=memory)

    return graph_mcp

# graph_mcp = react_agent(prompt, DeployInfo, examples, memory=False)