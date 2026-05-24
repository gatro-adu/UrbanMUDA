import json
import shutil
import os

class FileOp:
    def __init__(self):
        self.orders = {}

    def save_any_append(self, data, file_name, save_dir):
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        name = os.path.join(save_dir, file_name)
        with open(name, 'a', encoding='utf-8') as f:
            if isinstance(data, str):
                f.write(data)
            elif isinstance(data, dict) or isinstance(data, list):
                f.write(json.dumps(data, ensure_ascii=False))
            else:
                f.write(repr(data))
            f.write("\n")

    def save_list_replace(self, l, file_name, save_dir):
        if not os.path.exists(save_dir):
            os.makedirs(save_dir)
        name = os.path.join(save_dir, file_name)
        with open(name, 'w', encoding='utf-8') as f:
            f.write("orders = {\n")
            for key, value in enumerate(l):
                f.write(f"    \"order_{repr(key)}\": {repr(value)},\n")  # 使用 repr 确保正确格式化
            f.write("}\n")

    def move_files(self, names, src, dest):
        if not os.path.exists(dest):
            os.makedirs(dest)
        moved_files = []
        missing_files = []
        if isinstance(names, str):
            names = [names]
        if src.endswith(('/', '\\')):
            src = src[:-1]
        if dest.endswith(('/', '\\')):
            dest = dest[:-1]
        for name in names:
            src_file = os.path.join(src, name)
            dest_file = os.path.join(dest, name)
            if os.path.exists(src_file):
                shutil.move(src_file,dest_file)
                moved_files.append(name)
            else:
                missing_files.append(name)
        if missing_files:
            print(f'以下文件未找到: {missing_files}')

fileop = FileOp()