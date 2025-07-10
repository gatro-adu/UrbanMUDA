from langgraph.graph import END, StateGraph, START
from langgraph.checkpoint.memory import InMemorySaver
# from agent_retrieve.utils.nodes import generate, code_check, reflect
from agent_retrieve.utils.state import GraphState
from agent_retrieve.utils.tools import code_run
# from agent_retrieve.utils.chain import prompt
from agent_retrieve.utils.prompt import prompt
from scripts.workflow_react_no_struct_async import react_agent

# checkpointer = InMemorySaver()

# # Max tries
# max_iterations = 3
# # Reflect
# # flag = 'reflect'
# flag = "do not reflect"

# workflow = StateGraph(GraphState)

# # Define the nodes
# workflow.add_node("generate", generate)  # generation solution
# workflow.add_node("check_code", code_check)  # check code
# workflow.add_node("reflect", reflect)  # reflect

# # Build graph
# workflow.add_edge(START, "generate")
# workflow.add_edge("generate", "check_code")
# def decide_to_finish(state: GraphState):
#     error = state["error"]
#     iterations = state["iterations"]

#     if error == "no" or iterations == max_iterations:
#         print("---DECISION: FINISH---")
#         return "end"
#     else:
#         print("---DECISION: RE-TRY SOLUTION---")
#         if flag == "reflect":
#             return "reflect"
#         else:
#             return "generate"
# workflow.add_conditional_edges(
#     "check_code",
#     decide_to_finish,
#     {
#         "end": END,
#         "reflect": "reflect",
#         "generate": "generate",
#     },
# )
# workflow.add_edge("reflect", "generate")
# graph = workflow.compile(checkpointer=checkpointer)

graph = react_agent([code_run], prompt)


from langchain_mcp_adapters.client import MultiServerMCPClient

async def make_graph(memory: bool):
    client = MultiServerMCPClient({
        "main": {
            "command": "python",
            "args": ["mcp/retrieve_server.py"],
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
    graph_mcp = react_agent(tools, prompt, memory=memory)

    return graph_mcp
