def merge_tags(row):
    # 获取所有列名
    columns = list(row.index[1:-1])
    # 筛选出非 None 的值，并格式化为 "key=value" 的形式
    tags = [f"{col}={row[col]}" for col in columns if row[col] is not None]
    # 将所有标签合并为一个字符串，用逗号分隔
    return ",".join(tags)
def add_tags(df):
    df['tags'] = df.apply(merge_tags, axis=1)
    df.insert(loc=1, column='tags', value=df.pop('tags'))
    return df.drop(columns=list(df.columns[2:-1]))