from pathlib import Path
import sys
sys.path.append(str(Path(__file__).parent.parent.parent.parent))
import json

from pydantic import BaseModel, Field
from typing_extensions import Annotated
from langgraph.prebuilt import ToolNode
from langgraph.graph import MessagesState, StateGraph, END
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import ToolMessage
from scripts.llm_load import llm_gpt4omini as llm
from scripts.workflow_struct import struct_agent


def react_agent(tools, prompt, response_format, examples=[], llm=llm):
    class structure(BaseModel):
        '''Tool to get structured output'''
        output: Annotated[str, Field(desciption='Output to be structured')]
    tools = tools+[structure]
    class AgentState(MessagesState):
        final_response: response_format
    def call_model(state: AgentState):
        template = ChatPromptTemplate([
            ('system', f'{prompt}'),
            ('user', '{messages}')
        ])
        if examples:
            llm_with_tools = template|llm.bind_tools(tools)
        else:
            llm_with_tools = template|llm.bind_tools(tools, parallel_tool_calls=True)  # gpt非微调模型支持parallel_tool_calls下的strict模式
        response = llm_with_tools.invoke({'messages': state['messages']})
        return {'messages': [response]}
    def respond(state: AgentState):
        tool_call = state['messages'][-1].tool_calls[0]
        response = struct_agent(response_format, examples).invoke({'input': tool_call['args']['output']})
        print('\n===Unstructured Output===\n', tool_call['args']['output'])
        if not isinstance(response, dict):
            response = json.loads(response.model_dump_json())
        print('\n===Structured Output===\n', response, '\n')
        tool_message = ToolMessage(content='Here is your output', tool_call_id=tool_call['id'])
        return {'final_response': response, 'messages': [tool_message]}
    def should_continue(state: AgentState):
        messages = state['messages']
        last_message = messages[-1]
        if len(last_message.tool_calls)==1 and last_message.tool_calls[0]['name']=='structure':
            return 'respond'
        else: return 'continue'
    workflow = StateGraph(AgentState)
    workflow.add_node('agent', call_model).add_node('respond', respond).add_node('tools', ToolNode(tools)).set_entry_point('agent').add_conditional_edges('agent', should_continue, {'continue': 'tools', 'respond': 'respond'}).add_edge('tools', 'agent').add_edge('respond', END)
    agent = workflow.compile()
    return agent

