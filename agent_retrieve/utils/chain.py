from scripts.llm_load import llm_gpt4omini as llm
from scripts.workflow_react_async import react_agent
from scripts.workflow_struct import struct_agent
from agent_retrieve.utils.schema import code

### OpenAI

# prompt = """\
# You are a coding assistant with expertise in LCEL, LangChain expression language. \n 
# Here is a full set of LCEL documentation:  \n ------- \n  {context} \n ------- \n Answer the user 
# question based on the above provided documentation. Ensure any code you provide can be executed \n 
# with all required imports and variables defined. Structure your answer with a description of the code solution. \n
# Then list the imports. And finally list the functioning code block. Here is the user question:"""

prompt = """\
Answer the user question based on the above provided documentation. 
Ensure any code you provide can be executed with all required imports and variables defined. 
Structure your answer with a description of the code solution. 
Then list the imports. And finally list the functioning code block. 
Here is the user question:"""

prompt = '''\
你是一个擅长tortoise orm的专家，请根据我的需求查询数据库并回答问题。

<思考过程>
1. 根据用户的问题，确定需要查询的数据库表和字段。
2. 根据需要查询的数据库表和字段，使用Tortoise ORM框架生成对应的main.py代码。
3. 使用code_run工具运行该代码，并得到查询结果。
4. 最后使用structure工具输出用户问题的结果。
</思考过程>

<运行目录结构>
.
├── app
│   └── models.py
└── main.py
</运行目录结构>

<注意事项>
- Tortoise ORM模型定义在app/models.py中，直接从这个文件中导入即可。
- 当code_run工具运行错误时，请改正并重新使用code_run工具运行。
- 要使用Tortoise ORM，需要先初始化数据库，db_url='postgres://root:1234@localhost:5432/root'。
- 一段代码内不要有两个run_async(run)
</注意事项>

<运行报错解决方法>
- Multiple objects returned
    - 使用filter代替get
</运行报错解决方法>

<Tortoise ORM模型定义>
# app/models.py
class Tournament(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=255)

class Event(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=255)
    tournament = fields.ForeignKeyField('models.Tournament', related_name='events')
    participants = fields.ManyToManyField('models.Team', related_name='events', through='event_team')

class Team(Model):
    id = fields.IntField(primary_key=True)
    name = fields.CharField(max_length=255)
</Tortoise ORM模型定义>

<输出要求>
- 使用print将结果可视化打印
</输出要求>

Here is the user question:'''

code_gen_chain = struct_agent(code, prompt)

