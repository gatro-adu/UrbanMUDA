from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek
# from langchain_anthropic import ChatAnthropic
from langchain_ollama import OllamaEmbeddings, ChatOllama


llm_gpt4o = ChatOpenAI(
    model="gpt-4o",  # $10/m
    base_url="https://xiaoai.plus/v1",
    api_key="sk-7SK2UgajQRI2IFexXPJDnAM82f7uIP9Z2Rm4llGwv73l9MB8"
)
llm_gpt4omini = ChatOpenAI(
    model="gpt-4o-mini",  # $0.6/m
    base_url="https://xiaoai.plus/v1",
    api_key="sk-7SK2UgajQRI2IFexXPJDnAM82f7uIP9Z2Rm4llGwv73l9MB8"
)
# llm_gpt41mini = ChatOpenAI(
#     model="gpt-4.1-mini",  # $0.8/m
#     base_url="https://xiaoai.plus/v1",
#     api_key="sk-7SK2UgajQRI2IFexXPJDnAM82f7uIP9Z2Rm4llGwv73l9MB8"
# )
# llm_gpt41nano = ChatOpenAI(
#     model="gpt-4.1-nano",  # $0.2/m
#     base_url="https://xiaoai.plus/v1",
#     api_key="sk-7SK2UgajQRI2IFexXPJDnAM82f7uIP9Z2Rm4llGwv73l9MB8"
# )

# llm_deepseek = ChatDeepSeek(  # 不知道为什么，效果没有ChatOpenAI好
#     model="deepseek-chat", 
#     api_base="https://api.deepseek.com/v1",
#     api_key="sk-0be73b94b6fc40ebb62550fe7d4717bb"
# )
llm_deepseek = ChatOpenAI(
    model="deepseek-chat", 
    base_url="https://api.deepseek.com",
    api_key="sk-0be73b94b6fc40ebb62550fe7d4717bb"
)

llm_qwen_plus = ChatOpenAI(
    model='qwen-plus-latest',
    api_key = "sk-e625a5b815564cae9a0953a5a731976b",
    base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
)
llm_qwen_plus = ChatOpenAI(
    model='qwen-max-latest',
    api_key = "sk-e625a5b815564cae9a0953a5a731976b",
    base_url = "https://dashscope.aliyuncs.com/compatible-mode/v1"
)

# llm_claude = ChatAnthropic(
#     model_name="claude-3-5-haiku-20241022",
#     base_url="https://api.xiaoai.plus",
#     api_key="sk-p718ciGap99TstqcQAn7rxBFZLG65zRc5AV95MJfoMpFYR20"
# )

embedding = OllamaEmbeddings(model="nomic-embed-text")