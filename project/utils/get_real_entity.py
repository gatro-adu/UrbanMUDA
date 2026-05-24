import json
import os
from pathlib import Path
from difflib import SequenceMatcher
from scripts.similarity import similarity, geosimilarity

# 原始计算相似度
# def similarity(s1: str, s2: str) -> float:  
#     return SequenceMatcher(None, s1, s2).ratio()

entity_table_dir = 'project/datasets'

def get_real_entity(entity_name: str,k:int = 3) -> int|None:

    with open('project/datasets/装备实体列表.json', 'r', encoding='utf-8') as f:
        raw_data = json.load(f)

    entities = raw_data['data']

    # 计算每个数据项的相似度得分
    scores = []
    for item in entities:
        mname = item['mname']
        mdesc = item['mdesc']
        combined = mname
        if mdesc and mdesc.strip() != '':
            combined += ' ' + mdesc.strip()
        # 计算相似度
        # score = similarity(entity_name, combined)
        score = geosimilarity(entity_name, combined)
        scores.append((mname, item['id'], score))
    
    # 按照相似度得分从高到低排序
    scores.sort(key=lambda x: -x[2])
    
    # 提取前k个id
    result_ids = [(item[0],item[1]) for item in scores[:k]]  # (name, table_id)
    
    return result_ids[0]