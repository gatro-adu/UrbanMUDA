from shapely import Point
from collections import defaultdict

def flatten_nodes(node):
   """
   递归函数，用于展平读取每个装备或人员的名称和坐标
   """
   if node['nodetype'] in ['EquipNode', 'PersonnelNode']:
      name = node.get('name', '')
      position = node.get('position', [])  
      id = node.get('id', '')

      # agent_main
      if position:
         yield {'name': name, 'geometry': Point(position)}

      # agent_locate
      if id:
         yield {'name':name, 'id': id}

   if node['children'] is not None and node['children'] != 'null':
      for child in node['children']:
         yield from flatten_nodes(child)

def flatten(team):
   """
   提取 team 对象中每个装备或人员的名称和坐标
   """
   result = []
   for node in team['formations']:
      result.extend(flatten_nodes(node))
         
   return result