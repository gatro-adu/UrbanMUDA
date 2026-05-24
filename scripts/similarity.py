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

def geosimilarity(s1, s2):
    """计算综合相似度"""
    s1 = s1.lower()
    s2 = s2.lower()
    
    # 完全匹配
    if s1 == s2:
        return 1.0
        
    # 包含关系
    if s1 in s2 or s2 in s1:
        shorter, longer = sorted([len(s1), len(s2)])
        ratio = shorter / longer
        return 0.6 + 0.4 * ratio
        
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
    final_similarity = 0.3 * edit_similarity + 0.6 * lcs_similarity + 0.1 * overlap
    
    # 如果包含相同的汉字，提高相似度
    common_chars = set(c for c in s1 if '\u4e00' <= c <= '\u9fff') & set(c for c in s2 if '\u4e00' <= c <= '\u9fff')
    if common_chars:
        final_similarity += 0.1 * len(common_chars) / max(len(s1), len(s2))
        
    return min(1.0, final_similarity)
