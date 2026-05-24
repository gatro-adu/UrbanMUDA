import importlib.util

def load_py_vars(module_name, py_dir):
    spec = importlib.util.spec_from_file_location(module_name, py_dir)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)

    # 获取所有变量
    vars_dict = vars(module)

    # 过滤掉系统变量
    user_vars = {
        k: v for k, v in vars_dict.items()
        if not k.startswith("__")
    }
    return user_vars