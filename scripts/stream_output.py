import time
import uuid

from typing import Optional, Literal
from scripts.time_travel import print_state
from scripts.file_op import fileop
from fastapi.responses import StreamingResponse

def stream_output_chain(chain, inputs)->str:
    chunks=[]
    for chunk in chain.stream(inputs, stream_mode='messages'):
        chunks.append(chunk.content)
        print(chunk.content, end='', flush=True)
    return ''.join(chunks)

async def stream_output_graph(
    graph, 
    graph_input: Optional[dict], 
    config={'configurable': {'thread_id': uuid.uuid4()}}, 
    graph_name='MyGraph',
):
    turn = 0
    previous_time = time.time()
    async for node, state_raw in graph.astream(
        graph_input,
        subgraphs=True,
        stream_mode='debug',
        config=config
    ):
        state = state_raw['payload']
        fileop.save_any_append(state, f'datasets/jupyter/{graph_name[:5]}.py')

        if not state.get('values', {}).get('messages', []):
            continue
        print_state(state)
        # print("="*50, "state", "="*50)
        # print(state.get('values', {}).get('messages', [])[-1], '\n')
        
        turn += 1
        current_time = time.time()
        iteration_time = current_time - previous_time
        print(f"==={graph_name}=== 第{turn}次运行\n {node} 耗时: {iteration_time:.8f} 秒")
        previous_time = current_time

    return state.get('values', {})

