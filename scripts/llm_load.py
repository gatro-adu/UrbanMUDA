from langchain_openai import ChatOpenAI
from langchain_deepseek import ChatDeepSeek
from langchain_anthropic import ChatAnthropic
# from langchain_ollama import OllamaEmbeddings, ChatOllama
from pydantic import BaseModel
# from langchain_qwq import ChatQwen


class Models:
    def __init__(self):
        self.xiaoai = {
            "base_url": "https://xiaoai.plus/v1",
            "api_key": "sk-7SK2UgajQRI2IFexXPJDnAM82f7uIP9Z2Rm4llGwv73l9MB8"
        }
        self.deepseek = {
            "base_url": "https://api.deepseek.com",
            "api_key":"sk-0be73b94b6fc40ebb62550fe7d4717bb"
        }
        self.qwen = {
            "base_url": "sk-e625a5b815564cae9a0953a5a731976b",
            "api_key": "https://dashscope.aliyuncs.com/compatible-mode/v1"
        }
        self.a6000 = {
            "base_url": "http://localhost:10711",
            "api_key": "ollama"
        }

class Provider(BaseModel):
    api_key: str
    base_url: str


models = Models()
llm_main = ChatOpenAI(model='deepseek-chat', **models.deepseek)
llm_struct = ChatOpenAI(model='gpt-4o-mini', **models.xiaoai)
llm_deploy_rule = ChatOpenAI(model='gpt-4o-mini', **models.xiaoai)
llm_finetune = ChatOpenAI(model='gpt-4o-mini', **models.xiaoai)

# modelname_embedding = 'nomic-embed-text:latest'