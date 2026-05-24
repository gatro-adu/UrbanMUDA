import json
import copy

def print_state(state):
    message = state['values']['messages'][-1]
    message.pretty_print()

    print()
    if len(state['values']) > 1:
        print('==其他变量==')
        rest_values = copy.deepcopy(state['values'])
        rest_values.pop('messages')
        print(json.dumps(rest_values, indent=4, ensure_ascii=False))

    try:
        node_name = next(iter(state['metadata']['writes']))
    except:
        node_name = 'human'
    if node_name == '__start__':  # 强行纠正一个机制bug，问题不大
        node_name = 'human'
    print('==当前节点==')
    print(node_name)

    print('==当前config==')  # 其实是当前节点执行完毕的config，要修改这个结果，必须update父节点的config
    print(json.dumps({"configurable":state['config']['configurable']}, indent=4, ensure_ascii=False))

def print_states(states):
    for state in states[1:]:
        state = state._asdict()
        print_state(state)

def get_states(graph, config):
    real_config = {'configurable': {'thread_id': config['configurable']['thread_id']}}
    states = list(graph.get_state_history(real_config))
    states.reverse()
    
    return states

def get_state_by_config(graph, config) -> dict:
    return graph.get_state(config)._asdict()

def update_state_by_config(graph, config, values) -> dict:
    return graph.update_state(get_state_by_config(graph, config)['parent_config'], values=values)