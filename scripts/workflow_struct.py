from scripts.llm_load import llm_struct as llm
# from scripts.llm_load import llm_deepseek as llm
from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate

prompt_example = "Extract the information in accordance with the schema."

def struct_agent(response_format, prompt=prompt_example, examples=[], llm=llm):
    s = ''
    for d in examples:
        s += f'''Q：{d['input']}\nA：{d['output']}\n\n'''
    if examples:
        prompt_template = ChatPromptTemplate(
            [
                (
                    'system', prompt+f"""
examples: 
"""+s.replace("{", "{{").replace("}", "}}")+'使用json/JSON格式输出。'
                ),
                ('placeholder', '{messages}'),
            ]
        )
        # agent = prompt|llm.with_structured_output(method='json_mode')
        agent = prompt_template|llm.with_structured_output(schema=response_format, method='json_mode')
    else:
        # 不要删除！！！！！
        prompt_template = ChatPromptTemplate(
            [
                ('system', prompt),
                ('placeholder', '{messages}'),
            ]
        )
        agent = prompt_template|llm.with_structured_output(schema=response_format, strict=True)
    return agent