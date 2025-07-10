import json

from pydantic import BaseModel, Field
from typing_extensions import Annotated
from langgraph.prebuilt import ToolNode
from langgraph.graph import MessagesState, StateGraph, END
from langgraph.types import Command
from langgraph.checkpoint.memory import InMemorySaver
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.messages import ToolMessage
from scripts.llm_load import llm_gpt4omini as llm
from scripts.workflow_struct import struct_agent


def react_agent(tools, prompt='Use "structure" to output your final answer', response_format=[], examples=[], llm=llm, memory=True):
    class structure(BaseModel):
        '''Tool to get structured output'''
        output: Annotated[str, Field(desciption='Output to be structured')]
    class AgentState(MessagesState):
        final_response: list
    async def call_model(state: AgentState):
        template = ChatPromptTemplate([
            ('system', f'{prompt}'),
            ('user', '{messages}')
        ])
        real_tools = tools+[structure]
        llm_with_tools = template|llm.bind_tools(real_tools)
        response = await llm_with_tools.ainvoke({'messages': state['messages']})

        tool_call_names = [tc.get('name', '') for tc in response.tool_calls]

        if not response.tool_calls:
            update={"messages": [('tool', 'Here is your output')], 'final_response': [response.content]}
            goto = END
        elif len(set(tool_call_names))==1 and tool_call_names[0]=='structure':
            update = {"messages": [response], "final_response": [tc['args']['output'] for tc in response.tool_calls]}
            goto = END
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
        tool_call = state['messages'][-1].tool_calls[0]
        response = await struct_agent(response_format, examples).ainvoke({'input': tool_call['args']['output']})
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
    workflow.add_node('agent', call_model)\
    .add_node('tools', ToolNode(tools))\
    .set_entry_point('agent')\
    .add_edge('tools', 'agent')
    if memory:
        checkpointer = InMemorySaver()
        agent = workflow.compile(checkpointer=checkpointer)
    else: agent = workflow.compile()
    return agent

