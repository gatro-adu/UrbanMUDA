import json
import datetime
import os
import tempfile
from deepmerge import always_merger
from typing import Optional


def save_any(
        data: list|dict|str, 
        file_name: str, 
        save_dir:str, 
        method: Optional[str]='a', 
        file_name_time: Optional[bool]=False, 
        save_dir_time: Optional[bool]=False, 
        global_timestamp: Optional[str]=None,
        **kwargs
    ):
    if global_timestamp:
        timestamp = global_timestamp
    else:
        timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")

    try:
        first_name, last_name = file_name.rsplit('.', 1)
    except Exception:
        print({'file_name':file_name})
        raise
    if file_name_time:
        file_name = first_name + f'_{timestamp}.' + last_name

    if save_dir_time:
        save_dir = save_dir + f'_{timestamp}'
    
    if not os.path.exists(save_dir):
        os.makedirs(save_dir)
    path = os.path.join(save_dir, file_name)
    if method=='a':
        if last_name=='json':
            data_old = load_json_safe(path)
            if isinstance(data_old, dict):
                data = always_merger.merge(data_old, data)
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
            elif isinstance(data_old, list):
                data = data_old.append(data)
                with open(path, 'w', encoding='utf-8') as f:
                    json.dump(data, f, ensure_ascii=False, indent=2)
        elif last_name=='jsonl':
            with open(path, 'a', encoding='utf-8') as f:
                if isinstance(data, dict):
                    f.write(json.dumps(data, ensure_ascii=False) + '\n')
                elif isinstance(data, list):
                    for d in data:
                        f.write(json.dumps(d, ensure_ascii=False) + '\n')
        elif isinstance(data, str):
            with open(path, 'a', encoding='utf-8') as f:
                f.write(data+"\n")
    elif method=='w':
        if last_name=='json':
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        elif last_name=='jsonl':
            temp_dir = os.path.dirname(os.path.abspath(path))
            with tempfile.NamedTemporaryFile(mode='w', encoding='utf-8', dir=temp_dir, delete=False) as tmp_f:
                temp_path = tmp_f.name
                try:
                    if isinstance(data, dict):
                        tmp_f.write(json.dumps(data, ensure_ascii=False) + '\n')
                    elif isinstance(data, list):
                        for d in data:
                            tmp_f.write(json.dumps(d, ensure_ascii=False) + '\n')
                    # 此时临时文件已写入完成
                except Exception:
                    # 写入失败，删除临时文件并抛出异常
                    os.unlink(temp_path)
                    raise

            # 原子性地替换原文件（在大多数系统上是原子操作）
            os.replace(temp_path, path)
        elif isinstance(data, str):
            with open(path, 'w', encoding='utf-8') as f:
                f.write(data+"\n")

    return file_name


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