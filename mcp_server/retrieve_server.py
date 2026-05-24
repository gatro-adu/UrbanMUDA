import subprocess
import os

from typing import Annotated

from mcp.server.fastmcp import FastMCP
mcp = FastMCP("Retrieve")

prefix = '''\
from pathlib import Path
current_dir = Path.cwd()
import sys, os
sys.path.append(os.getcwd())
from app.models import DeploymentEquipment, DeploymentRule\n'''

code_prefix = '''\
from tortoise import Tortoise, run_async
from app.models import DeploymentEquipment, DeploymentRule

async def init_db():
    await Tortoise.init(
        db_url='sqlite://EquipRules.sqlite3',
        modules={'models': ['app.models']}
    )
    await Tortoise.generate_schemas()
    
async def main():
    try:
        await init_db()
        <你的代码>
    finally:
        await Tortoise.close_connections()'''

@mcp.tool()
def code_run(
    # imports: Annotated[str, "The imports to be added to the .py file"],
    # code: Annotated[str, "The code without imports to be added to the .py file"],
    code: Annotated[str, f"请续写：{code_prefix}。"],
):
    """Tool to run generated code"""

    print("---CHECKING CODE---")

    file_path = os.path.abspath('datasets/tortoise/main.py')
    target_dir = os.path.dirname(file_path)

    # # 先写入import 试试
    # with open('datasets/tortoise/main.py', 'w', encoding='utf-8') as f:
    #     f.write(prefix + imports)
        
    # try:
    #     # exec(imports)
    #     subprocess.run(['python', file_path], cwd=target_dir)
    # except Exception as e:
    #     print("---CODE IMPORT CHECK: FAILED---")
    #     return f"Your solution failed the import test: {e}"
    
    # 再写入代码
    with open('datasets/tortoise/main.py', 'w', encoding='utf-8') as f:
        f.write(prefix + code)
    try:
        # exec(code)
        result = subprocess.run(
            ['python', file_path],
            cwd=target_dir,
            capture_output=True,  # 捕获输出
            text=True,           # 返回字符串而非字节
        )
        # print("="*50, "代码执行结果", "="*50)
        # print("Return code:", result.returncode)  # 0=成功，非0=失败
        # print("stdout:", result.stdout)          # 子进程的print输出
        if result.stderr:
            print("="*50, "代码执行报错", "="*50)
            print("stderr:", result.stderr, '\n')          # 子进程的错误输出
    except Exception as e:
        print("---CODE BLOCK CHECK: FAILED---")
        return f"Your solution failed the code execution test: {e}"

    # No errors
    print("---NO CODE TEST FAILURES---")
    return f"{result.stdout}"

if __name__ == "__main__":
    mcp.run(transport="stdio")