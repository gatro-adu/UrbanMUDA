from scripts.llm_load import llm_gpt4omini as llm
# from scripts.llm_load import llm_deepseek as llm
from langchain_core.prompts import ChatPromptTemplate, FewShotChatMessagePromptTemplate

prompt_example = "Extract the information in accordance with the schema."

def struct_agent(response_format, prompt=prompt_example, examples=[], llm=llm):
    # example_prompt = ChatPromptTemplate(
    #     [
    #         ('user', '{input}'),
    #         ('ai', '{output}')
    #     ]
    # )
    # few_shot_prompt = FewShotChatMessagePromptTemplate(
    #     examples=examples,
    #     example_prompt=example_prompt
    # )
    s = ''
    for d in examples:
        s += f'''Q：{d['input']}\nA：{d['output']}\n\n'''
    if examples:
#         prompt = ChatPromptTemplate(
#             [
#                 (
#                     'system',
#                     '''\
# You are an expert at structured data extraction. 
# You will be given unstructured text and should convert it into the given structure.
# Below are few-shot examples: '''
#                 ),
#                 few_shot_prompt,
#                 ('system', 'Please structure the following inputs with json referring to the above few-shot examples'),
#                 ('human', '{input}'),
#             ]
        # )
        prompt_template = ChatPromptTemplate(
            [
                (
                    'system', prompt+f"""
examples: 
"""+s.replace("{", "{{").replace("}", "}}")
                ),
                ('placeholder', '{messages}'),
            ]
        )
        # agent = prompt|llm.with_structured_output(method='json_mode')
        agent = prompt_template|llm.with_structured_output(schema=response_format, method='function_calling')
    else:
        # 不要删除！！！！！
        prompt_template = ChatPromptTemplate(
            [
                ('system', prompt),
                ('placeholder', '{messages}'),
            ]
        )
        agent = prompt_template|llm.with_structured_output(schema=response_format, strict=True)

        # prompt = ChatPromptTemplate(
        #     [
        #         (
        #             'system', f"""Extract the deployment scenario information."""
        #         ),
        #         ('user', '{input}'),
        #     ]
        # )
        # agent = prompt|llm.with_structured_output(schema=response_format, method='function_calling')
    
    return agent