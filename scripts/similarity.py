import re
from collections import Counter
import unicodedata
from collections import defaultdict
from functools import partial
from itertools import groupby

def normalize_text(text):
    """
    更全面的文本标准化处理
    处理打印习惯带来的常见变异
    """
    # 转换为小写
    text = text.lower()
    
    # 统一全角半角字符
    text = unicodedata.normalize('NFKC', text)
    
    # 常见打印错误替换
    common_typos = {
        'o': '0',
        'l': '1',
        'z': '2',
        's': '5',
        'b': '6',
        'g': '9',
        # 添加更多常见打印混淆字符
    }
    
    # 双向替换表
    replacement_map = {}
    for k, v in common_typos.items():
        replacement_map[k] = v
        replacement_map[v] = k
    
    # 执行替换
    normalized = []
    for char in text:
        normalized.append(replacement_map.get(char, char))
    text = ''.join(normalized)
    
    # 移除所有非字母数字字符，但保留汉字
    text = re.sub(r'[^\w\u4e00-\u9fff]', '', text)
    
    return text

def levenshtein_distance(s1, s2):
    """优化后的编辑距离计算"""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            # 考虑打印习惯的相似字符
            if c1 == c2 or (c1 in {'0', 'o', 'O'} and c2 in {'0', 'o', 'O'}) or (c1 in {'1', 'l', 'i'} and c2 in {'1', 'l', 'i'}):
                substitutions = previous_row[j]
            else:
                substitutions = previous_row[j] + 1
            current_row.append(min(previous_row[j + 1] + 1,  # 删除
                                 current_row[j] + 1,       # 插入
                                 substitutions))            # 替换
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
    """改进的综合相似度计算，考虑打印习惯"""
    s1 = normalize_text(s1)
    s2 = normalize_text(s2)
    
    # 完全匹配
    if s1 == s2:
        return 1.0
        
    # 包含关系（考虑部分匹配）
    if s1 in s2 or s2 in s1:
        min_len = min(len(s1), len(s2))
        max_len = max(len(s1), len(s2))
        return 0.7 + 0.2 * (min_len / max_len)  # 基础分+长度比例分
        
    # 计算编辑距离相似度（考虑打印习惯）
    max_len = max(len(s1), len(s2))
    edit_sim = 1 - (levenshtein_distance(s1, s2) / max_len)
    
    # 计算LCS相似度
    lcs_sim = lcs_length(s1, s2) / max_len
    
    # 计算字符重叠度（考虑字符频率）
    counter1 = Counter(s1)
    counter2 = Counter(s2)
    intersection = sum((counter1 & counter2).values())
    union = sum((counter1 | counter2).values())
    overlap_sim = intersection / union if union > 0 else 0
    
    # 计算拼音相似度（针对中文）
    pinyin_sim = 0
    if any('\u4e00' <= c <= '\u9fff' for c in s1 + s2):
        try:
            from pypinyin import pinyin, Style
            pinyin1 = [item[0] for item in pinyin(s1, style=Style.NORMAL)]
            pinyin2 = [item[0] for item in pinyin(s2, style=Style.NORMAL)]
            pinyin_intersection = len(set(pinyin1) & set(pinyin2))
            pinyin_union = len(set(pinyin1) | set(pinyin2))
            pinyin_sim = pinyin_intersection / pinyin_union if pinyin_union > 0 else 0
        except ImportError:
            pass
    
    # 综合评分
    weights = {
        'edit': 0.35,
        'lcs': 0.25,
        'overlap': 0.2,
        'pinyin': 0.2
    }
    final_sim = (weights['edit'] * edit_sim + 
                 weights['lcs'] * lcs_sim + 
                 weights['overlap'] * overlap_sim + 
                 weights['pinyin'] * pinyin_sim)
    
    # 对短字符串的补偿
    if max_len < 5:
        final_sim = min(1.0, final_sim * (1 + 0.1 * (5 - max_len)))
    
    return min(1.0, max(0.0, final_sim))

def normalize_special_pattern(text):
    """
    精确处理带有括号和数字后缀的特殊模式
    返回(前缀, 括号内容, 数字后缀)三元组
    """
    pattern1 = re.compile(r'^(.*?)（([^（）]+)）$')
    pattern2 = re.compile(r'^(.*?)_(\d+)（([^（）]+)）$')
    
    match = pattern2.match(text) or pattern1.match(text)
    if match:
        groups = match.groups()
        return (groups[0], groups[-1], groups[1] if len(groups) > 2 else None)
    return None

def enhanced_similarity(query, candidate):
    """
    增强的相似度计算，优先考虑完整包含查询词的情况
    """
    # 如果候选完全包含查询词，给予更高分数
    if query in candidate:
        return 0.9 + 0.1 * similarity(query, candidate)
    
    # 如果查询词完全包含候选词（如查询"军用卡车"包含候选"卡车"）
    if candidate in query:
        return 0.7 + 0.3 * similarity(query, candidate)
    
    # 普通相似度计算
    return similarity(query, candidate)

def exact_word_match_list(
    keyword: str, 
    word_list: list, 
    threshold: float = 0.55,
    prefix_check: bool = True
) -> list:
    """
    改进的精确匹配函数，优先匹配包含完整查询词的项
    """
    keyword_parts = normalize_special_pattern(keyword)
    
    matches = []
    for word in word_list:
        if not word:
            continue
            
        # 特殊模式处理
        if keyword_parts:
            word_parts = normalize_special_pattern(word)
            if word_parts:
                # 括号内容必须匹配
                if keyword_parts[1] != word_parts[1]:
                    continue
                
                # 检查前缀关系
                # if prefix_check and not word_parts[0].startswith(keyword_parts[0]):
                #     continue
                if not word_parts[0].startswith(keyword_parts[0]):
                    continue
                
                # 计算分数（包含完整前缀的分数更高）
                score = 0.9 if word_parts[0].startswith(keyword_parts[0]) else 0.7
                num = int(word_parts[2]) if word_parts[2] else 0
                matches.append((word, score, num))
                continue
        
        # 普通文本匹配
        score = enhanced_similarity(keyword, word)
        if score >= threshold:
            num = 0  # 普通匹配项数字设为0
            matches.append((word, score, num))
    
    # 排序规则：
    # 1. 首先按是否完全包含查询词（降序）
    # 2. 然后按分数（降序）
    # 3. 最后按数字（升序）
    matches.sort(key=lambda x: (
        -int(keyword in x[0]),  # 完全包含查询词的优先
        -x[1],                  # 分数高的优先
        x[2]                    # 数字小的优先
    ))
    if not matches:
        return []
    if prefix_check:
        for key, group in groupby(matches):
            return [g[0] for g in list(group)]
    else:
        return [match[0] for match in matches]