import json

class FileOp:
    def __init__(self):
        self.orders = {}

    def save_any_append(self, data, path):
        with open(path, 'a', encoding='utf-8') as f:
            f.write(repr(data))
            f.write("\n")
    def save_list_replace(self, l, path):
        with open(path, 'w', encoding='utf-8') as f:
            f.write("orders = {\n")
            for key, value in enumerate(l):
                f.write(f"    \"order_{repr(key)}\": {repr(value)},\n")  # 使用 repr 确保正确格式化
            f.write("}\n")

fileop = FileOp()