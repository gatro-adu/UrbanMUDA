import json

def convert(js):
   def deep_parse_json(data):
      """
      递归解析嵌套的 JSON 字符串，支持字典、列表和元组。
      """
      if isinstance(data, dict):
            # 如果是字典，递归处理每个键值对
            return {key: deep_parse_json(value) for key, value in data.items()}
      elif isinstance(data, (list, tuple)):
            # 如果是列表或元组，递归处理每个元素
            # 注意：元组在解析后需要转换回元组
            parsed_list = [deep_parse_json(item) for item in data]
            return tuple(parsed_list) if isinstance(data, tuple) else parsed_list
      elif isinstance(data, str):
            # 如果是字符串，尝试解析为 JSON
            try:
               parsed_data = json.loads(data)
               # 如果解析成功，递归处理解析后的数据
               return deep_parse_json(parsed_data)
            except json.JSONDecodeError:
               # 如果解析失败，说明这不是 JSON 字符串，直接返回原字符串
               return data
      else:
            # 其他类型直接返回
            return data
   return json.dumps(deep_parse_json(js), ensure_ascii=False)