# 定义装饰器
def register_method(label):
    def decorator(method):
        method._registered = True  # 标记方法需要注册
        method._label = label      # 存储标签
        return method
    return decorator


# 定义元类
class TaskMeta(type):
    def __new__(cls, name, bases, namespace):
        # 创建类
        new_class = super().__new__(cls, name, bases, namespace)
        
        # 初始化未绑定的方法注册表
        new_class._unbound_method_map = {}
        
        # 遍历类的所有属性
        for attr_name, attr_value in namespace.items():
            # 检查是否是方法且被标记为需要注册
            if callable(attr_value) and getattr(attr_value, '_registered', False):
                label = getattr(attr_value, '_label', 'default')
                new_class._unbound_method_map[label] = attr_value
        
        return new_class
