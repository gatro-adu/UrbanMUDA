from copy import deepcopy

def merge_nodes_json(n1: dict, n2: dict) -> dict:
    assert n1['id'] == n2['id'] and n1['nodetype'] == n2['nodetype']

    merged_children = merge_node_list_json(n1.get('children'), n2.get('children'))
    return {
        'nodetype': n1['nodetype'],
        'name': n1['name'],
        'id': n1['id'],
        'children': merged_children
    }

def merge_node_list_json(l1, l2):
    if not l1:
        return deepcopy(l2) if l2 else []
    if not l2:
        return deepcopy(l1)

    result = []
    map1 = {n['id']: n for n in l1 if n.get('id') and n['id'] != 'null'}
    map2 = {n['id']: n for n in l2 if n.get('id') and n['id'] != 'null'}

    common_ids = set(map1) & set(map2)
    for cid in common_ids:
        if map1[cid]['nodetype'] == map2[cid]['nodetype']:
            result.append(merge_nodes_json(map1[cid], map2[cid]))
        else:
            result.append(deepcopy(map1[cid]))
            result.append(deepcopy(map2[cid]))

    for cid in set(map1) - common_ids:
        result.append(deepcopy(map1[cid]))
    for cid in set(map2) - common_ids:
        result.append(deepcopy(map2[cid]))

    # 加入无 id 的节点
    for n in l1 + l2:
        if not n.get('id') or n['id'] == 'null':
            result.append(deepcopy(n))

    return result

def merge_team_json(t1: dict | None, t2: dict | None) -> dict | None:
    if t1 is None and t2 is None:
        return None
    if t1 is None:
        return deepcopy(t2)
    if t2 is None:
        return deepcopy(t1)

    f1 = t1.get('formations') or []
    f2 = t2.get('formations') or []
    merged_formations = merge_node_list_json(f1, f2)

    return {'formations': merged_formations}

def merge_delete_infos_json(d1: dict, d2: dict) -> dict:
    return {
        'red': merge_team_json(d1.get('red'), d2.get('red')),
        'blue': merge_team_json(d1.get('blue'), d2.get('blue'))
    }