import json
import re

def load_json_safe(path, default=None):
    if default is None:
        default = {}
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except FileNotFoundError:
        # 安全创建
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(default, f, ensure_ascii=False, indent=2)
        except OSError:
            pass  # 无法写入（权限/磁盘满等），但至少不崩溃
        return default
    except (json.JSONDecodeError, OSError) as e:
        # 文件损坏或读取错误
        print(f"Warning: {path} is corrupted or unreadable: {e}")
        return default

def load_markdown_safe(path, default="", encoding='utf-8'):
    """
    安全读取 Markdown 文件
    
    Args:
        path: 文件路径
        default: 读取失败时的默认值
        encoding: 文件编码，默认 utf-8
    
    Returns:
        str: 文件内容或默认值
    """
    try:
        with open(path, 'r', encoding=encoding) as f:
            content = f.read()
            # 验证是否为有效的文本内容
            if isinstance(content, str):
                return content
            else:
                print(f"Warning: {path} contains invalid content")
                return default
    except FileNotFoundError:
        # 文件不存在，创建默认文件
        try:
            with open(path, 'w', encoding=encoding) as f:
                f.write(default)
        except OSError:
            pass  # 无法写入，但不崩溃
        return default
    except (UnicodeDecodeError, OSError) as e:
        # 文件编码错误或读取错误
        print(f"Warning: {path} is corrupted or unreadable: {e}")
        return default

# # 使用示例
# content = load_markdown_safe('README.md', '# Default Title\n\nEmpty content')

def parse_json_from_markdown(text: str):
    # 第一步：如果是被转义的字符串，先反转义
    if '\\"' in text:
        text = json.loads(f'"{text}"')  # 只解 JSON 转义，不碰中文
    

    # 第二步：提取 ```json ... ```
    match = re.search(
        r'```(?:json)?\s*([\s\S]*?)\s*```',
        text
    )

    json_str = match.group(1) if match else text

    # 第三步：解析 JSON
    return json.loads(json_str)

# def function_tool_to_pure_json_schema(tool: dict) -> dict:
#     """
#     将 OpenAI function/tool schema 转换为纯 JSON Schema
#     规则：
#     - 去掉 type=function、strict、function 外壳
#     - 提取 function.parameters
#     - 合并 $defs 中的 enum（如 IntentType）到 properties
#     """

#     if tool.get("type") != "function":
#         raise ValueError("Not a function tool schema")

#     parameters = tool["function"]["parameters"]

#     # 深拷贝，避免修改原对象
#     schema = {
#         "title": parameters.get("title"),
#         "type": parameters.get("type", "object"),
#         "required": parameters.get("required", []),
#         "additionalProperties": parameters.get("additionalProperties", True),
#         "properties": {},
#     }

#     defs = parameters.get("$defs", {})

#     for prop, spec in parameters.get("properties", {}).items():
#         # 如果是 $ref，展开 enum
#         if spec.get('enum'):
#             spec.pop('enum')
#         if "$ref" in spec:
#             ref_name = spec["$ref"].split("/")[-1]
#             if ref_name in defs:
#                 schema["properties"][prop] = {
#                     "title": defs[ref_name].get("title"),
#                     "type": defs[ref_name].get("type", "string"),
#                     # "enum": defs[ref_name].get("enum"),
#                 }
#             else:
#                 schema["properties"][prop] = spec
#         else:
#             schema["properties"][prop] = spec

#     return schema

def function_tool_to_pure_json_schema(tool: dict) -> dict:
    """
    将 OpenAI function/tool schema 转换为「语义占位 JSON」
    每个字段值形如：
      ["这里输出xxx"]
    明确告诉模型该字段该做什么
    """

    if tool.get("type") != "function":
        raise ValueError("Not a function tool schema")

    params = tool["function"]["parameters"]
    defs = params.get("$defs", {})

    template = {}

    for prop, spec in params.get("properties", {}).items():
        # 默认语义提示
        hint = f"这里输出{prop}"

        # 如果字段有 description，用 description
        if "description" in spec:
            hint = f"这里输出{spec['description']}"

        # 如果是 $ref，补充 enum 语义
        if "$ref" in spec:
            ref_name = spec["$ref"].split("/")[-1]
            enum = defs.get(ref_name, {}).get("enum")
            if enum or (enum := spec.get('enum')):
                hint += f"，取值只能是 {enum}"

        template[prop] = hint

    return template


