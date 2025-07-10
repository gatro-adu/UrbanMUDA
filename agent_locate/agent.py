from scripts.workflow_react import react_agent
from agent_locate.utils.tools import get_nearby_entities, get_entity
from agent_locate.utils.rules import default, tool, think
from agent_locate.utils.schema import DeleteInfo, examples


rules = f'''\
<默认规则>{default}</默认规则>
<工具规则>{tool}</工具规则>
<思考规则>{think}</思考规则>'''

prompt = f'''\
你是一个兵力实体删除专家。根据用户输入的兵力删除指令，确定被删除的编组或兵力实体。
最后使用structure输出符合删除指令的兵力实体信息，包括name、所属team、id。请务必涵盖用户输入中提及的所有编组或兵力实体。
你需要注意的规则如下：
{rules}'''

## 普通tools
tools = [get_nearby_entities, get_entity]
graph = react_agent(tools, prompt, DeleteInfo, examples)


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
            "args": ["mcp/locate_server.py"],
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
    graph_mcp = react_agent(tools, prompt, DeleteInfo, examples, memory=memory)

    return graph_mcp