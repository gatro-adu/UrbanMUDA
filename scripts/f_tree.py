from pydantic import BaseModel, Field
from typing import Literal

# class FTreeNode(BaseModel):
#     EquipChildrenID: list[str]
#     CommanderChildrenID: list[str]
#     ParentID: str
#     NodeID: str
#     Name: str
#     Strength: str
#     Quantity: str
#     NodeType: Literal["Entity", "Commander"]

class FTreeNode:
    def __init__(self):
        self.NodeType = None
        self.NodeID = None
        self.Name = None
        self.Children = []  # 存储子节点的NodeID和类型
        self.Parent = None  # 父节点的NodeID
        self.CustomAttributes = {}  # 存储自定义属性

    def AddChildID(self, child_id, child_type):
        self.Children.append((child_id, child_type))

    def SetParent(self, parent_id):
        self.Parent = parent_id

    def AddAttribute(self, key, value):
        self.CustomAttributes[key] = value

    def GetAttribute(self, key):
        return self.CustomAttributes.get(key)


class FTreeNodeType:
    CommanderNode = "CommanderNode"
    EquipNode = "EquipNode"
    PersonnelNode = "PersonnelNode"


def levenshtein_distance(s1, s2):
    """计算编辑距离"""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    return previous_row[-1]


def lcs_length(s1, s2):
    """计算最长公共子序列长度"""
    m, n = len(s1), len(s2)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(1, m + 1):
        for j in range(1, n + 1):
            if s1[i-1] == s2[j-1]:
                dp[i][j] = dp[i-1][j-1] + 1
            else:
                dp[i][j] = max(dp[i-1][j], dp[i][j-1])
    return dp[m][n]


def similarity(s1, s2):
    """计算综合相似度"""
    s1 = s1.lower()
    s2 = s2.lower()
    
    # 完全匹配
    if s1 == s2:
        return 1.0
        
    # 包含关系
    if s1 in s2 or s2 in s1:
        return 0.9
        
    # 计算编辑距离相似度
    max_len = max(len(s1), len(s2))
    edit_similarity = 1 - (levenshtein_distance(s1, s2) / max_len)
    
    # 计算LCS相似度
    lcs_similarity = lcs_length(s1, s2) / max_len
    
    # 计算字符重叠度
    set1 = set(s1)
    set2 = set(s2)
    overlap = len(set1 & set2) / len(set1 | set2)
    
    # 综合评分
    final_similarity = 0.4 * edit_similarity + 0.3 * lcs_similarity + 0.3 * overlap
    
    # 如果包含相同的汉字，提高相似度
    common_chars = set(c for c in s1 if '\u4e00' <= c <= '\u9fff') & set(c for c in s2 if '\u4e00' <= c <= '\u9fff')
    if common_chars:
        final_similarity += 0.1 * len(common_chars) / max(len(s1), len(s2))
        
    return min(1.0, final_similarity)


def find_similar_names(name, database, similarity_threshold=0.6, max_results=5):
    """
    在数据库中查找相似名称
    :param name: 要查找的名称
    :param database: 数据库字典
    :param similarity_threshold: 相似度阈值，默认0.6
    :param max_results: 最大返回结果数，默认5
    :return: 相似度高于阈值的名称列表，按相似度降序排列
    """
    # 计算所有名称的相似度
    similarities = [(key, similarity(name, key)) for key in database.keys()]
    
    # 过滤掉低于阈值的名称
    similarities = [(key, sim) for key, sim in similarities if sim >= similarity_threshold]
    
    # 按相似度排序
    similarities.sort(key=lambda x: x[1], reverse=True)
    
    # 返回结果，最多返回max_results个
    return similarities[:max_results]


def get_node_path(node_map, node_id):
    """获取从指定节点到根节点的完整路径（从底层到高层）"""
    path = []
    current = node_map.get(node_id)
    while current:
        path.append(current.Name)
        current = node_map.get(current.Parent)
    return " <= ".join(path)


def get_base_name(name):
    """获取节点名称的基础部分（去除后缀数字）"""
    import re
    match = re.match(r"(.*?)(?:_\d+)?$", name)
    return match.group(1) if match else name


def get_max_suffix(node_map, parent_id, base_name):
    """获取指定父节点下同名节点的最大后缀编号"""
    parent = node_map[parent_id]
    max_suffix = 0
    
    # 遍历所有子节点
    for child_id, _ in parent.Children:
        child = node_map.get(child_id)
        if not child:
            continue
            
        # 检查节点名称是否匹配基础名称
        if child.Name.startswith(base_name):
            # 尝试提取后缀数字
            import re
            match = re.match(rf"{base_name}_(\d+)$", child.Name)
            if match:
                suffix = int(match.group(1))
                max_suffix = max(max_suffix, suffix)
            elif child.Name == base_name:
                # 如果没有后缀，视为0
                max_suffix = max(max_suffix, 0)
                
    return max_suffix


def rename_existing_nodes(node_map, base_name, parent_id):
    """为所有同名节点添加数字后缀"""
    # 获取父节点下的所有子节点
    parent = node_map[parent_id]
    existing_nodes = [(child_id, node_map[child_id]) for child_id, _ in parent.Children]
            
    # 找出所有同名节点（包括没有后缀的）
    same_name_nodes = [(node_id, node) for node_id, node in existing_nodes 
                      if node.Name == base_name or node.Name.startswith(base_name + "_")]
            
    # 如果没有同名节点，不需要重命名
    if not same_name_nodes:
        return
                
    # 为所有同名节点添加数字后缀
    for i, (node_id, node) in enumerate(same_name_nodes, 1):
        node.Name = f"{base_name}_{i}"


def get_unique_name(node_map, base_name, parent_id, rename_existing=True):
    """获取唯一的节点名称，自动添加数字后缀
    
    Args:
        node_map: 节点映射表
        base_name: 基础名称
        parent_id: 父节点ID
        rename_existing: 是否重命名已存在的同名节点，默认为True
    """
    if not parent_id:  # 根节点不需要检查
        return base_name
        
    # 获取基础名称
    base = get_base_name(base_name)
    
    # 获取最大后缀编号
    max_suffix = get_max_suffix(node_map, parent_id, base)
    
    # 如果基础名称已经存在，使用下一个编号
    if max_suffix > 0 or any(node.Name == base for _, node in [(child_id, node_map[child_id]) for child_id, _ in node_map[parent_id].Children]):
        if rename_existing:
            rename_existing_nodes(node_map, base, parent_id)
        return f"{base}_{max_suffix + 1}"
        
    return base


def create_node(tree, node_info, parent=None):
    """创建节点及其子节点"""
    # 生成节点ID
    node_id = tree.generate_node_id(
        node_info.get("NodeType", FTreeNodeType.CommanderNode),
        parent.NodeID if parent else None
    )
            
    node = FTreeNode()
    node.NodeType = node_info.get("NodeType", FTreeNodeType.CommanderNode)
    node.NodeID = node_id
    # 使用get_unique_name生成节点名称
    node.Name = get_unique_name(tree.node_map, node_info["Name"], parent.NodeID if parent else None)
    tree.node_map[node.NodeID] = node

    if parent:
        parent.AddChildID(node.NodeID, node.NodeType)
        node.SetParent(parent.NodeID)

    # 处理子节点
    for child_info in node_info.get("Children", []):
        # 如果是人员或装备节点，根据数量创建多个节点
        if child_info.get("NodeType") in [FTreeNodeType.PersonnelNode, FTreeNodeType.EquipNode]:
            quantity = child_info.get("Quantity", 1)
            base_name = child_info["Name"]
                    
            # 检查名称是否在数据库中
            if child_info["NodeType"] == FTreeNodeType.EquipNode:
                database = equipment_database
            else:
                database = personnel_database
                    
            if base_name not in database:
                print(f"\n===错误：未找到 '{base_name} <= {get_node_path(tree.node_map, node.NodeID)}'===")
                print(f"{'装备' if child_info['NodeType'] == FTreeNodeType.EquipNode else '人员'}数据库中有如下相似名称：")
                similar_names = find_similar_names(base_name, database)
                for i, (name, similarity) in enumerate(similar_names, 1):
                    print(f"{i}. {name} (相似度: {similarity:.2f})")
                choice = input("请选择正确的名称编号（输入0表示取消）：")
                if choice == "0":
                    continue
                try:
                    base_name = similar_names[int(choice)-1][0]
                except (ValueError, IndexError):
                    print("无效的选择，跳过此节点")
                    continue
                    
            # 创建多个节点
            for i in range(quantity):
                child_node = FTreeNode()
                child_node.NodeType = child_info["NodeType"]
                # 为每个节点生成新的ID，确保编号从1开始
                child_node.NodeID = tree.generate_node_id(child_info["NodeType"], node.NodeID)
                # 使用get_unique_name生成节点名称
                child_node.Name = get_unique_name(tree.node_map, f"{base_name}_{i+1}", node.NodeID)
                        
                # 添加数据库中的默认属性
                if child_info["NodeType"] == FTreeNodeType.EquipNode:
                    child_node.AddAttribute("参数", equipment_database[base_name]["参数"])
                else:
                    child_node.AddAttribute("技能", personnel_database[base_name]["技能"])
                        
                child_node.SetParent(node.NodeID)
                node.AddChildID(child_node.NodeID, child_node.NodeType)
                tree.node_map[child_node.NodeID] = child_node
        else:
            # 对于指挥官节点，递归创建
            create_node(tree, child_info, node)

    return node


class FTree:
    def __init__(self, root=None):
        self.root = root
        self.node_map = {}
        self.node_counter = {}  # 用于记录每种类型的节点数量

    def find_node_by_path(self, path_str, similarity_threshold=0.6):
        """通过节点路径查找节点
        
        Args:
            path_str: 节点路径字符串，用分隔符分隔的节点名称序列
                    例如："迫击炮排/迫击炮班/男步枪手_2（台）"
            similarity_threshold: 相似度阈值，默认0.6
            
        Returns:
            tuple: (匹配的节点, 路径相似度, 完整路径)
                  如果没有找到匹配的节点，返回(None, 0, "")
        """
        if not path_str:
            return None, 0, ""
            
        # 分割路径
        path_parts = path_str.split('/')
        if not path_parts:
            return None, 0, ""
            
        # 计算路径相似度
        def calculate_path_similarity(node, current_path, remaining_parts):
            """递归计算路径相似度"""
            if not remaining_parts:
                # 已经匹配到路径末尾
                return node, 1.0, current_path
                
            current_part = remaining_parts[0]
            best_match = None
            best_similarity = 0
            best_path = ""
            
            # 计算当前节点名称与目标名称的相似度
            current_similarity = similarity(node.Name, current_part)
            
            if current_similarity >= similarity_threshold:
                # 如果当前节点匹配，继续匹配子节点
                for child_id, _ in node.Children:
                    child = self.node_map.get(child_id)
                    if not child:
                        continue
                        
                    match, sim, path = calculate_path_similarity(
                        child, 
                        f"{current_path}/{child.Name}" if current_path else child.Name,
                        remaining_parts[1:]
                    )
                    
                    if sim > best_similarity:
                        best_match = match
                        best_similarity = sim
                        best_path = path
                        
                if best_match:
                    # 返回子节点匹配结果
                    return best_match, best_similarity * current_similarity, best_path
                    
            # 如果没有匹配的子节点，检查当前节点是否匹配完整路径
            if len(remaining_parts) == 1 and current_similarity >= similarity_threshold:
                return node, current_similarity, current_path
                
            return None, 0, ""
            
        # 从根节点开始搜索
        if not self.root:
            return None, 0, ""
            
        return calculate_path_similarity(self.root, self.root.Name, path_parts)

    def generate_node_id(self, node_type, parent_id=None):
        """自动生成节点ID"""
        # 获取节点类型前缀
        prefix = {
            FTreeNodeType.CommanderNode: "CMD",
            FTreeNodeType.PersonnelNode: "PER",
            FTreeNodeType.EquipNode: "EQP"
        }.get(node_type, "UNK")
        
        if parent_id:
            # 如果是子节点，使用父节点ID作为前缀，并从1开始计数
            if parent_id not in self.node_counter:
                self.node_counter[parent_id] = {}
            if prefix not in self.node_counter[parent_id]:
                self.node_counter[parent_id][prefix] = 0
            self.node_counter[parent_id][prefix] += 1
            return f"{parent_id}_{prefix}{self.node_counter[parent_id][prefix]}"
        else:
            # 如果是根节点，使用全局计数器
            if prefix not in self.node_counter:
                self.node_counter[prefix] = 0
            self.node_counter[prefix] += 1
            return f"{prefix}{self.node_counter[prefix]}"

    def create_from_battalion_info(self, battalion_info):
        """从编组信息创建树"""
        self.node_map = {}  # 清空映射表
        self.node_counter = {}  # 重置计数器

        # 从传入的编组信息中创建树
        root_info = battalion_info["Root"]
        self.root = create_node(self, root_info)
        return self

    def print_tree(self, node=None, level=0):
        """打印树结构"""
        if node is None:
            node = self.root
        indent = "  " * level
        print(f"{indent}节点ID: {node.NodeID}, 名称: {node.Name}, 类型: {node.NodeType}")
        
        # 打印自定义属性
        if node.CustomAttributes:
            print(f"{indent}  自定义属性:")
            for key, value in node.CustomAttributes.items():
                if isinstance(value, dict):
                    print(f"{indent}    {key}:")
                    for sub_key, sub_value in value.items():
                        print(f"{indent}      {sub_key}: {sub_value}")
                else:
                    print(f"{indent}    {key}: {value}")
        
        for child_id, child_type in node.Children:
            child = self.node_map.get(child_id)
            if child:
                self.print_tree(child, level + 1)

    def add_node_to_tree(self, parent_node_id, new_node_info):
        """添加新节点到树中
        
        Args:
            parent_node_id: 父节点ID
            new_node_info: 新节点信息，可以是字典、FTree对象或FTreeNode对象
                - 如果是字典：包含Name, NodeType, CustomAttributes等信息
                - 如果是FTree对象：将整个子树添加到指定父节点下
                - 如果是FTreeNode对象：将节点及其所有子节点添加到树中
        """
        parent = self.node_map.get(parent_node_id)
        if not parent:
            print(f"错误：未找到父节点 {parent_node_id}")
            return None
            
        if isinstance(new_node_info, FTree):
            # 添加子树
            subtree = new_node_info
            if not subtree.root:
                print("错误：子树为空")
                return None
                
            # 创建节点ID映射表，用于记录新旧ID的对应关系
            id_mapping = {}
            
            # 使用队列进行广度优先遍历
            from collections import deque
            queue = deque()
            
            # 处理根节点
            root_id = self.generate_node_id(subtree.root.NodeType, parent_node_id)
            id_mapping[subtree.root.NodeID] = root_id
            
            # 创建新的根节点
            new_root = FTreeNode()
            new_root.NodeType = subtree.root.NodeType
            new_root.NodeID = root_id
            new_root.Name = subtree.root.Name  # 直接使用原始名称
            new_root.CustomAttributes = subtree.root.CustomAttributes.copy()
            new_root.SetParent(parent_node_id)
            
            # 将新根节点添加到树中
            self.node_map[root_id] = new_root
            parent.AddChildID(root_id, new_root.NodeType)
            
            # 将根节点加入队列
            queue.append((subtree.root, new_root))
            
            # 处理所有子节点
            while queue:
                old_node, new_parent = queue.popleft()
                
                # 处理所有子节点
                for child_id, child_type in old_node.Children:
                    old_child = subtree.node_map.get(child_id)
                    if not old_child:
                        continue
                        
                    # 生成新的子节点ID
                    new_child_id = self.generate_node_id(old_child.NodeType, new_parent.NodeID)
                    id_mapping[old_child.NodeID] = new_child_id
                    
                    # 创建新的子节点
                    new_child = FTreeNode()
                    new_child.NodeType = old_child.NodeType
                    new_child.NodeID = new_child_id
                    new_child.Name = old_child.Name  # 直接使用原始名称
                    new_child.CustomAttributes = old_child.CustomAttributes.copy()
                    new_child.SetParent(new_parent.NodeID)
                    
                    # 将新子节点添加到树中
                    self.node_map[new_child_id] = new_child
                    new_parent.AddChildID(new_child_id, new_child.NodeType)
                    
                    # 将子节点加入队列
                    queue.append((old_child, new_child))
                    
            return new_root
            
        elif isinstance(new_node_info, FTreeNode):
            # 添加FTreeNode对象及其所有子节点
            old_root = new_node_info
            
            # 创建节点ID映射表，用于记录新旧ID的对应关系
            id_mapping = {}
            
            # 使用队列进行广度优先遍历
            from collections import deque
            queue = deque()
            
            # 处理根节点
            root_id = self.generate_node_id(old_root.NodeType, parent_node_id)
            id_mapping[old_root.NodeID] = root_id
            
            # 创建新的根节点
            new_root = FTreeNode()
            new_root.NodeType = old_root.NodeType
            new_root.NodeID = root_id
            new_root.Name = old_root.Name  # 直接使用原始名称
            new_root.CustomAttributes = old_root.CustomAttributes.copy()
            new_root.SetParent(parent_node_id)
            
            # 将新根节点添加到树中
            self.node_map[root_id] = new_root
            parent.AddChildID(root_id, new_root.NodeType)
            
            # 将根节点加入队列
            queue.append((old_root, new_root))
            
            # 处理所有子节点
            while queue:
                old_node, new_parent = queue.popleft()
                
                # 处理所有子节点
                for child_id, child_type in old_node.Children:
                    # 获取原始子节点
                    old_child = self.node_map.get(child_id)
                    if not old_child:
                        continue
                        
                    # 生成新的子节点ID
                    new_child_id = self.generate_node_id(old_child.NodeType, new_parent.NodeID)
                    id_mapping[old_child.NodeID] = new_child_id
                    
                    # 创建新的子节点
                    new_child = FTreeNode()
                    new_child.NodeType = old_child.NodeType
                    new_child.NodeID = new_child_id
                    new_child.Name = old_child.Name  # 直接使用原始名称
                    new_child.CustomAttributes = old_child.CustomAttributes.copy()
                    new_child.SetParent(new_parent.NodeID)
                    
                    # 将新子节点添加到树中
                    self.node_map[new_child_id] = new_child
                    new_parent.AddChildID(new_child_id, new_child.NodeType)
                    
                    # 将子节点加入队列
                    queue.append((old_child, new_child))
                    
            return new_root
            
        else:
            # 添加单个节点（字典形式）
            node_id = self.generate_node_id(
                new_node_info.get("NodeType", FTreeNodeType.CommanderNode),
                parent_node_id
            )
                
            node = FTreeNode()
            node.NodeType = new_node_info.get("NodeType", FTreeNodeType.CommanderNode)
            node.NodeID = node_id
            node.Name = new_node_info["Name"]  # 直接使用原始名称
            
            # 添加自定义属性
            for key, value in new_node_info.get("CustomAttributes", {}).items():
                node.AddAttribute(key, value)
                
            node.SetParent(parent_node_id)
            parent.AddChildID(node.NodeID, node.NodeType)
            self.node_map[node.NodeID] = node
            return node

    def add_attributes_to_node(self, node_id, attributes):
        """为节点添加自定义属性"""
        node = self.node_map.get(node_id)
        if not node:
            print(f"错误：未找到节点 {node_id}")
            return False
            
        for key, value in attributes.items():
            node.AddAttribute(key, value)
        return True

    def get_total_personnel(self, node=None):
        """计算树中所有人员节点的总数"""
        personnel_nodes = self.find_nodes_by_type(FTreeNodeType.PersonnelNode)
        return len(personnel_nodes)

    def find_node_by_id(self, node_id):
        """通过ID查找节点"""
        return self.node_map.get(node_id)

    def get_node_path(self, node_id):
        """获取从指定节点到根节点的完整路径（从底层到高层）"""
        return get_node_path(self.node_map, node_id)

    def find_nodes_by_name(self, name, node_type=None, similarity_threshold=0.6):
        """查找名称相似的节点"""
        results = []
        for node_id, node in self.node_map.items():
            if node_type and node.NodeType != node_type:
                continue
                
            sim = similarity(name, node.Name)
            if sim >= similarity_threshold:
                results.append((node, sim, self.get_node_path(node_id)))
                
        # 按相似度排序
        results.sort(key=lambda x: x[1], reverse=True)
        return results

    def find_and_select_node(self, name, node_type=None, similarity_threshold=0.6):
        """查找名称相似的节点并让用户选择"""
        results = self.find_nodes_by_name(name, node_type, similarity_threshold)
        
        if not results:
            print(f"未找到与 '{name}' 相似的节点")
            return None
            
        if len(results) == 1:
            return results[0][0]
            
        print(f"\n查找'{name}'，找到 {len(results)} 个相似节点：")
        for i, (node, sim, path) in enumerate(results, 1):
            print(f"{i}. 路径: {path} (相似度: {sim:.2f})")
            
        choice = input("请选择节点编号（输入0表示取消）：")
        if choice == "0":
            return None
            
        try:
            return results[int(choice)-1][0]
        except (ValueError, IndexError):
            print("无效的选择")
            return None

    def find_nodes_by_type(self, node_type):
        """查找指定类型的所有节点"""
        return [node for node in self.node_map.values() if node.NodeType == node_type]

    def find_nodes_by_attribute(self, attribute_key, attribute_value):
        """查找具有指定属性的节点
        
        Args:
            attribute_key: 属性键，支持点号分隔的嵌套属性（如"技能.射击"）
            attribute_value: 属性值
        """
        results = []
        
        def get_nested_value(obj, key_path):
            """获取嵌套属性值"""
            keys = key_path.split('.')
            current = obj
            for key in keys:
                if isinstance(current, dict) and key in current:
                    current = current[key]
                else:
                    return None
            return current
            
        for node in self.node_map.values():
            if attribute_key in node.CustomAttributes:
                # 直接属性匹配
                if node.CustomAttributes[attribute_key] == attribute_value:
                    results.append(node)
            else:
                # 尝试嵌套属性匹配
                value = get_nested_value(node.CustomAttributes, attribute_key)
                if value == attribute_value:
                    results.append(node)
                    
        return results

    def remove_node(self, node_id):
        """删除指定节点及其所有子节点
        
        Args:
            node_id: 要删除的节点ID
            
        Returns:
            bool: 是否成功删除
        """
        # 获取要删除的节点
        node = self.node_map.get(node_id)
        if not node:
            print(f"错误：未找到节点 {node_id}")
            return False
            
        # 如果是根节点，直接清空树
        if node == self.root:
            self.root = None
            self.node_map = {}
            self.node_counter = {}
            return True
            
        # 获取父节点
        parent = self.node_map.get(node.Parent)
        if not parent:
            print(f"错误：未找到父节点 {node.Parent}")
            return False
            
        # 递归删除所有子节点
        def remove_children(node_id):
            node = self.node_map.get(node_id)
            if not node:
                return
                
            # 递归删除所有子节点
            for child_id, _ in node.Children:
                remove_children(child_id)
                
            # 从节点映射表中删除当前节点
            del self.node_map[node_id]
            
        # 开始删除
        remove_children(node_id)
        
        # 从父节点的子节点列表中移除
        parent.Children = [(child_id, child_type) for child_id, child_type in parent.Children 
                         if child_id != node_id]
                         
        return True

    def disband_group(self, commander_id):
        """解散指定指挥员节点，将其子节点转移到父节点下
        
        Args:
            commander_id: 要解散的指挥员节点ID
            
        Returns:
            bool: 是否成功解散
        """
        # 获取要解散的指挥员节点
        commander = self.node_map.get(commander_id)
        if not commander:
            print(f"错误：未找到指挥员节点 {commander_id}")
            return False
            
        # 检查节点类型
        if commander.NodeType != FTreeNodeType.CommanderNode:
            print(f"错误：节点 {commander_id} 不是指挥员节点")
            return False
            
        # 获取父节点
        parent = self.node_map.get(commander.Parent)
        if not parent:
            print(f"错误：未找到父节点 {commander.Parent}")
            return False
            
        # 获取所有子节点
        children = [(child_id, child_type) for child_id, child_type in commander.Children]
        
        # 将子节点转移到父节点下
        for child_id, child_type in children:
            child = self.node_map.get(child_id)
            if child:
                # 生成新的节点ID
                new_child_id = self.generate_node_id(child_type, parent.NodeID)
                
                # 更新子节点的ID和父节点
                child.NodeID = new_child_id
                child.SetParent(parent.NodeID)
                
                # 将子节点添加到父节点的子节点列表中
                parent.AddChildID(new_child_id, child_type)
                
                # 更新节点映射表
                del self.node_map[child_id]
                self.node_map[new_child_id] = child
                
        # 从父节点的子节点列表中移除指挥员节点
        parent.Children = [(child_id, child_type) for child_id, child_type in parent.Children 
                         if child_id != commander_id]
                         
        # 从节点映射表中删除指挥员节点
        del self.node_map[commander_id]
        
        return True

    def to_ftreenode(self):
        """将FTree转换为FTreeNode形式
        
        Returns:
            FTreeNode: 转换后的根节点，包含所有子节点
        """
        pass

    def rename_nodes_from_id(self, start_node_id):
        """从指定节点开始，重命名所有同名节点（去掉后缀后同名）
        
        Args:
            start_node_id: 开始重命名的节点ID
            
        Returns:
            bool: 是否成功重命名
        """
        # 获取起始节点
        start_node = self.node_map.get(start_node_id)
        if not start_node:
            print(f"错误：未找到节点 {start_node_id}")
            return False
            
        # 获取基础名称（去掉后缀）
        base_name = get_base_name(start_node.Name)
        
        # 获取所有需要重命名的节点
        nodes_to_rename = []
        def collect_nodes(node_id):
            node = self.node_map.get(node_id)
            if not node:
                return
                
            # 如果节点名称的基础部分匹配，添加到重命名列表
            if get_base_name(node.Name) == base_name:
                nodes_to_rename.append(node)
                
            # 递归处理子节点
            for child_id, _ in node.Children:
                collect_nodes(child_id)
                
        # 从起始节点开始收集需要重命名的节点
        collect_nodes(start_node_id)
        
        # 如果没有需要重命名的节点，直接返回
        if not nodes_to_rename:
            return True
            
        # 按节点ID排序，确保重命名顺序一致
        nodes_to_rename.sort(key=lambda x: x.NodeID)
        
        # 重命名所有节点
        for i, node in enumerate(nodes_to_rename, 1):
            node.Name = f"{base_name}_{i}"
            
        return True


if __name__ == "__main__":
    node_map = {}
    # 装备和人员数据库
    equipment_database = {
        "运输车": {
            "类型": "车辆",
            "参数": {
                "载重": "5吨",
                "速度": "80km/h",
                "续航": "500km"
            }
        },
        "120mm车载迫击炮": {
            "类型": "火炮",
            "参数": {
                "射程": "8km",
                "射速": "15发/分",
                "精度": "0.95"
            }
        },
        "95式自动步枪": {
            "类型": "轻武器",
            "参数": {
                "射程": "400m",
                "射速": "650发/分",
                "弹匣容量": "30发"
            }
        },
        "M1A1主战坦克": {
            "类型": "装甲车辆",
            "参数": {
                "射程": "400m",
                "射速": "650发/分",
                "弹匣容量": "30发"
            }
        },
        "M1A2主战坦克（美）": {
            "类型": "装甲车辆",
            "参数": {
                "射程": "400m",
                "射速": "650发/分",
                "弹匣容量": "30发"
            }
        },
    }

    personnel_database = {
        "男步枪手_1（台）": {
            "类型": "人员",
            "技能": {
                "射击": 0.6,
                "装填": 0.9,
            }
        },
        "男狙击手_1（台）": {
            "类型": "人员",
            "技能": {
                "射击": 0.9,
                "装填": 0.8,
            }
        },
        "男步枪手_2（台）": {
            "类型": "人员",
            "技能": {
                "射击": 0.6,
                "装填": 0.9,
            }
        },
        "男狙击手_2（台）": {
            "类型": "人员",
            "技能": {
                "射击": 0.9,
                "装填": 0.8,
            }
        },
        "男步枪手_1（中）": {
            "类型": "人员",
            "技能": {
                "射击": 0.6,
                "装填": 0.9,
            }
        },
        "男步枪手_2（中）": {
            "类型": "人员",
            "技能": {
                "射击": 0.6,
                "装填": 0.9,
            }
        },
        "男狙击手_1（中）": {
            "类型": "人员",
            "技能": {
                "射击": 0.9,
                "装填": 0.8,
            }
        },
        "男狙击手_2（中）": {
            "类型": "人员",
            "技能": {
                "射击": 0.9,
                "装填": 0.8,
            }
        },
    }

    '''\
    现在有编组信息：蓝军迫击炮排编制24人，辖排部和3个迫击炮班。排部编制6人，配运输车1辆，每个120mm车载迫击炮班编制6人，配120mm车载迫击炮1门。
    '''
    # 示例编组信息参数
    battalion_info = {
        "Root": {
            "Name": "迫击炮排",
            "NodeType": FTreeNodeType.CommanderNode,
            "Children": [
                {
                    "Name": "排部",
                    "NodeType": FTreeNodeType.CommanderNode,
                    "Children": [
                        {
                            "Name": "男步枪手_1（台）",
                            "NodeType": FTreeNodeType.PersonnelNode,
                            "Quantity": 3
                        },
                        {
                            "Name": "M1A2主战坦克",
                            "NodeType": FTreeNodeType.EquipNode,
                            "Quantity": 1
                        }
                    ]
                },
                {
                    "Name": "迫击炮班_1",
                    "NodeType": FTreeNodeType.CommanderNode,
                    "Children": [
                        {
                            "Name": "男步枪手_1（中）",
                            "NodeType": FTreeNodeType.PersonnelNode,
                            "Quantity": 3
                        },
                        {
                            "Name": "120mm车载迫击炮",
                            "NodeType": FTreeNodeType.EquipNode,
                            "Quantity": 1
                        }
                    ]
                },
                {
                    "Name": "迫击炮班_2",
                    "NodeType": FTreeNodeType.CommanderNode,
                    "Children": [
                        {
                            "Name": "步枪手_2（台）",
                            "NodeType": FTreeNodeType.PersonnelNode,
                            "Quantity": 2
                        },
                        {
                            "Name": "120mm车载迫击炮",
                            "NodeType": FTreeNodeType.EquipNode,
                            "Quantity": 1
                        }
                    ]
                },
                {
                    "Name": "迫击炮班_3",
                    "NodeType": FTreeNodeType.CommanderNode,
                    "Children": [
                        {
                            "Name": "男狙击手_2（中）",
                            "NodeType": FTreeNodeType.PersonnelNode,
                            "Quantity": 2
                        },
                        {
                            "Name": "120mm车载迫击炮",
                            "NodeType": FTreeNodeType.EquipNode,
                            "Quantity": 1
                        }
                    ]
                }
            ]
        }
    }
    # 修改create_battalion_tree函数
    def create_battalion_tree(battalion_info):
        """创建编组树"""
        tree = FTree()
        return tree.create_from_battalion_info(battalion_info)

    # 创建编组树
    tree = create_battalion_tree(battalion_info)

    # 创建迫击炮班的子树
    vehicle_tree = create_battalion_tree({
        "Root": {
            "Name": "步战车班",
            "NodeType": FTreeNodeType.CommanderNode,
            "Children": [
                {
                    "Name": "男步枪手_2（中）",
                    "NodeType": FTreeNodeType.PersonnelNode,
                    "Quantity": 2
                },
                {
                    "Name": "120mm车载迫击炮",
                    "NodeType": FTreeNodeType.EquipNode,
                    "Quantity": 1
                }
            ]
        }
    })
    tree.add_node_to_tree("CMD1_CMD1", vehicle_tree)
    node = tree.find_node_by_id("CMD1_CMD1_CMD1")
    if node: print(f"\n===<通过树> 成功添加节点: {node.Name}===")
    else: print(f"\n===<通过树> 添加节点{node.Name}失败===")

    # 创建迫击炮班的子树
    vehicle_tree = create_battalion_tree({
        "Root": {
            "Name": "步战车班",
            "NodeType": FTreeNodeType.CommanderNode,
            "Children": [
                {
                    "Name": "男狙击手_2（中）",
                    "NodeType": FTreeNodeType.PersonnelNode,
                    "Quantity": 1
                },
                {
                    "Name": "M1A1主战坦克",
                    "NodeType": FTreeNodeType.EquipNode,
                    "Quantity": 2
                }
            ]
        }
    })
    tree.add_node_to_tree("CMD1_CMD1", vehicle_tree)  # 
    node = tree.find_node_by_id("CMD1_CMD1_CMD2")
    if node: print(f"\n===<通过树> 成功添加节点: {node.Name}===")
    else: print(f"\n===<通过树> 添加节点{node.Name}失败")

    # 创建迫击炮班的子树
    vehicle_tree = create_battalion_tree({
        "Root": {
            "Name": "步战车班_1",
            "NodeType": FTreeNodeType.CommanderNode,
            "Children": [
                {
                    "Name": "男狙击手_2（中）",
                    "NodeType": FTreeNodeType.PersonnelNode,
                    "Quantity": 1
                },
                {
                    "Name": "M1A1主战坦克",
                    "NodeType": FTreeNodeType.EquipNode,
                    "Quantity": 2
                }
            ]
        }
    })
    tree.add_node_to_tree("CMD1_CMD1", vehicle_tree)
    node = tree.find_node_by_id("CMD1_CMD1_CMD3")
    if node: print(f"\n===<通过树> 成功添加节点: {node.Name}===")
    else: print(f"\n===<通过树> 添加节点{node.Name}失败")

    # 统计总人数
    total = tree.get_total_personnel()
    print(f"\n===计算总人数: {total}===")

    node = tree.find_node_by_path("迫击炮排/迫击炮班_1/男步枪手_1（台）")
    if node: print(f"\n===<通过路径> 找到节点: {node[0].Name}===")
    else: print(f"\n===<通过路径> 找节点失败===")

    # # 打印树结构
    # tree.print_tree()

    # 查找特定类型的节点
    nodes = tree.find_nodes_by_type(FTreeNodeType.PersonnelNode)
    print(f"\n===<通过类型> 找到 {len(nodes)} 个人员节点===")

    # 查找具有特定属性的节点
    nodes = tree.find_nodes_by_attribute("技能.射击", 0.9)
    print(f"\n===<通过属性> 找到 {len(nodes)} 个射击技能为0.9的节点===")

    # 查找节点
    node = tree.find_and_select_node("迫击炮")
    if node: print(f"\n===<通过名称> 找到节点: {node.Name}===")
    else: print(f"\n===<通过名称> 找节点失败===")

    # 删除节点及其所有子节点
    success = tree.remove_node("CMD1_CMD1_CMD3")
    if success:
        print("\n===节点删除成功===")
    else:
        print("\n===节点删除失败===")

    # 假设有一个指挥员节点ID为"CMD1_CMD2"
    success = tree.disband_group("CMD1_CMD2")
    if success:
        print("\n===编组解散成功===")
    else:
        print("\n===编组解散失败===")

    # print(tree.node_map.get("CMD1"))
    tree.rename_nodes_from_id("CMD1")
    tree.print_tree()