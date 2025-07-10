from langchain_core.messages import AIMessage, ToolMessage, HumanMessage

def print_messages(messages: list[AIMessage|ToolMessage|HumanMessage]) -> None:
    for message in messages:
        message.pretty_print()

if __name__ == '__main__':
    my_list = ['finish', 'cal', 'cal', 'finish', 'cal', 'finish']  # 示例列表

    # 自定义排序规则
    order = {'finish': 0, 'cal': 1}  # 定义排序优先级
    my_list.sort(key=lambda x: order[x])  # 使用自定义规则排序

    print(my_list)