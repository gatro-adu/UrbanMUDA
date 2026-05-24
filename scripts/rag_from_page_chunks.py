import json
import os
import re
import hashlib
import sys
import concurrent.futures
import random
import time
import ollama
import asyncio
import anyio
import threading
import numpy as np
from ollama import AsyncClient
from typing import List, Dict, Any
from tqdm import tqdm
from http import client
from openai import OpenAI
from dotenv import load_dotenv 
from typing import List, Dict, Optional, Tuple
from openai import RateLimitError
from numpy import dot
from numpy.linalg import norm

# LOCAL_API_KEY,LOCAL_BASE_URL,LOCAL_TEXT_MODEL,LOCAL_EMBEDDING_MODEL

load_dotenv()  # 加载环境变量（可选，用户可自行读取）



def get_openai_client(api_key: str, base_url: str) -> OpenAI:
    """
    获取 OpenAI 客户端，必须传递 api_key 和 base_url
    """
    if not api_key or not base_url:
        raise ValueError("api_key 和 base_url 必须显式传递！")
    return OpenAI(
        api_key=api_key,
        base_url=base_url,
    )


async def batch_get_embeddings(
    texts: List[str],
    batch_size: int = 64,
    api_key: str = None,
    base_url: str = None,
    embedding_model: str = None
) -> List[List[float]]:
    """
    批量获取文本的嵌入向量
    :param texts: 文本列表
    :param batch_size: 批处理大小
    :param api_key: 可选，自定义 API KEY
    :param base_url: 可选，自定义 BASE URL
    :param embedding_model: 可选，自定义嵌入模型
    :return: 嵌入向量列表
    """
    # if not api_key or not base_url or not embedding_model:
    #     raise ValueError("api_key、base_url、embedding_model 必须显式传递！")
    all_embeddings = []
    # client = get_openai_client(api_key, base_url)
    total = len(texts)
    if isinstance(texts, str):
        print(texts)
    if total == 0:
        return []
    iterator = range(0, total, batch_size)
    if total > 1:
        iterator = tqdm(iterator, desc="Embedding", unit="batch")

    # 修改点
    client = AsyncClient()
    async def task(batch_texts):
        response = await client.embed(
            model='nomic-embed-text:latest',
            input=batch_texts,
            keep_alive='30m'
        )
        batch_embeddings = response['embeddings']
        # all_embeddings.extend(batch_embeddings)
        return batch_embeddings
    tasks = []

    for i in iterator:
        batch_texts = texts[i:i + batch_size]
        retry_count = 0
        # while True:
        #     try:
        #         response = ollama.embed(
        #             model='quentinz/bge-base-zh-v1.5',
        #             input=batch_texts
        #         )
        #         batch_embeddings = response['embeddings']
        #         all_embeddings.extend(batch_embeddings)
        #         break
        #     except RateLimitError as e:
        #         retry_count += 1
        #         print(f"RateLimitError: {e}. 等待10秒后重试（第{retry_count}次）...")
        #         time.sleep(10)

        # 修改点
        tasks.append(asyncio.create_task(task(batch_texts)))
    # results_raw = asyncio.run(asyncio.gather(*tasks))
    results_raw = await asyncio.gather(*tasks)
    for result_raw in results_raw:
        all_embeddings.extend(result_raw)
        
    return all_embeddings

def get_text_embedding(
    texts: List[str],
    api_key: str = None,
    base_url: str = None,
    embedding_model: str = None,
    batch_size: int = 64
) -> List[List[float]]:
    """
    获取文本的嵌入向量，支持批次处理，保持输出顺序与输入顺序一致
    :param texts: 文本列表
    :param api_key: 可选，自定义 API KEY
    :param base_url: 可选，自定义 BASE URL
    :param embedding_model: 可选，自定义嵌入模型
    :param batch_size: 批处理大小
    :return: 嵌入向量列表
    """
    # if not api_key or not base_url or not embedding_model:
    #     raise ValueError("api_key、base_url、embedding_model 必须显式传递！")
    # 直接批量获取所有文本的embedding，不做缓存
    result = None

    def runner():
        nonlocal result
        result = anyio.run(batch_get_embeddings, 
            texts,
            batch_size,
            api_key,
            base_url,
            embedding_model
        )

    t = threading.Thread(target=runner)
    t.start()
    t.join()

    return result
    # return anyio.run(batch_get_embeddings, 
    #     texts,
    #     batch_size,
    #     api_key,
    #     base_url,
    #     embedding_model
    # )


class PageChunkLoader:
    def __init__(self, json_path: str):
        self.json_path = json_path
    def load_chunks(self) -> List[Dict[str, Any]]:
        with open(self.json_path, 'r', encoding='utf-8') as f:
            return json.load(f)


class EmbeddingModel:
    def __init__(self, batch_size: int = 64):
        self.api_key = os.getenv('LOCAL_API_KEY')
        self.base_url = os.getenv('LOCAL_BASE_URL')
        self.embedding_model = os.getenv('LOCAL_EMBEDDING_MODEL')
        self.batch_size = batch_size
        # if not self.api_key or not self.base_url:
        #     raise ValueError('请在.env中配置LOCAL_API_KEY和LOCAL_BASE_URL')

    def embed_texts(self, texts: List[str]) -> List[List[float]]:
        return get_text_embedding(
            texts,
            api_key=self.api_key,
            base_url=self.base_url,
            embedding_model=self.embedding_model,
            batch_size=self.batch_size
        )

    def embed_text(self, text: str) -> List[float]:
        return self.embed_texts([text])[0]

class SimpleVectorStore:
    def __init__(self):
        self.embeddings = []
        self.chunks = []
    def add_chunks(self, chunks: List[Dict[str, Any]], embeddings: List[List[float]]):
        self.chunks.extend(chunks)
        self.embeddings.extend(embeddings)
    def search(self, query_embedding: List[float], top_k: int = 3) -> List[Dict[str, Any]]:

        if not self.embeddings:
            return []
        emb_matrix = np.array(self.embeddings)
        query_emb = np.array(query_embedding)
        sims = emb_matrix @ query_emb / (norm(emb_matrix, axis=1) * norm(query_emb) + 1e-8)
        idxs = sims.argsort()[::-1][:top_k]
        return [self.chunks[i] for i in idxs]
    def sims(self, query_embedding: List[float], top_k: int = 3) -> np.ndarray:

        if not self.embeddings:
            return []
        emb_matrix = np.array(self.embeddings)
        query_emb = np.array(query_embedding)
        sims = emb_matrix @ query_emb / (norm(emb_matrix, axis=1) * norm(query_emb) + 1e-8)
        return sims
        # idxs = sims.argsort()[::-1][:top_k]
        # return [float(sims[i]) for i in idxs]

class SimpleRAG:
    def __init__(self, chunk_json_path: str, model_path: str = None, batch_size: int = 32):
        self.loader = PageChunkLoader(chunk_json_path)
        self.embedding_model = EmbeddingModel(batch_size=batch_size)
        self.vector_store = SimpleVectorStore()
    def setup(self):
        print("加载所有页chunk...")
        chunks = self.loader.load_chunks()
        print(f"共加载 {len(chunks)} 个chunk")
        print("生成嵌入...")
        embeddings = self.embedding_model.embed_texts([c['content'] for c in chunks])
        print("存储向量...")
        self.vector_store.add_chunks(chunks, embeddings)
        print("RAG向量库构建完成！")
    def query(self, question: str, top_k: int = 3) -> Dict[str, Any]:
        q_emb = self.embedding_model.embed_text(question)
        results = self.vector_store.search(q_emb, top_k)
        return {
            "question": question,
            "chunks": results
        }

    def generate_answer(self, question: str, top_k: int = 3) -> Dict[str, Any]:
        """
        检索+大模型生成式回答，返回结构化结果
        """
        qwen_api_key = os.getenv('LOCAL_API_KEY')
        qwen_base_url = os.getenv('LOCAL_BASE_URL')
        qwen_model = os.getenv('LOCAL_TEXT_MODEL')
        if not qwen_api_key or not qwen_base_url or not qwen_model:
            raise ValueError('请在.env中配置LOCAL_API_KEY、LOCAL_BASE_URL、LOCAL_TEXT_MODEL')
        q_emb = self.embedding_model.embed_text(question)
        chunks = self.vector_store.search(q_emb, top_k)
        # 拼接检索内容，带上元数据
        context = "\n".join([
            f"[文件名]{c['metadata']['file_name']} [页码]{c['metadata']['page']}\n{c['content']}" for c in chunks
        ])
        # 明确要求输出JSON格式 answer/page/filename
        prompt = (
            f"你是一名专业的金融分析助手，请根据以下检索到的内容回答用户问题。\n"
            f"请严格按照如下JSON格式输出：\n"
            f'{{"answer": "你的简洁回答", "filename": "来源文件名", "page": "来源页码"}}'"\n"
            f"检索内容：\n{context}\n\n问题：{question}\n"
            f"请确保输出内容为合法JSON字符串，不要输出多余内容。"
        )
        client = OpenAI(api_key=qwen_api_key, base_url=qwen_base_url)
        completion = client.chat.completions.create(
            model=qwen_model,
            messages=[
                {"role": "system", "content": "你是一名专业的金融分析助手。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.2,
            max_tokens=1024
        )

        if raw_content := completion.choices[0].message.content:
            raw = raw_content.strip()
        else:
            raw = ''
        # 用 extract_json_array 提取 JSON 对象
        json_str = extract_json_array(raw, mode='objects')
        if json_str:
            try:
                arr = json.loads(json_str)
                # 只取第一个对象
                if isinstance(arr, list) and arr:
                    j = arr[0]
                    answer = j.get('answer', '')
                    filename = j.get('filename', '')
                    page = j.get('page', '')
                else:
                    answer = raw
                    filename = chunks[0]['metadata']['file_name'] if chunks else ''
                    page = chunks[0]['metadata']['page'] if chunks else ''
            except Exception:
                answer = raw
                filename = chunks[0]['metadata']['file_name'] if chunks else ''
                page = chunks[0]['metadata']['page'] if chunks else ''
        else:
            answer = raw
            filename = chunks[0]['metadata']['file_name'] if chunks else ''
            page = chunks[0]['metadata']['page'] if chunks else ''
        # 结构化输出
        return {
            "question": question,
            "answer": answer,
            "filename": filename,
            "page": page,
            "retrieval_chunks": chunks
        }


    
def extract_json_array(text: str, mode: str = 'auto'):
    """
    从字符串中提取第一个 JSON 数组或由多个对象组成的数组。

    mode:
      - 'auto': 优先提取 ```json 代码块，其次是独立的 [] 数组，最后是由多个 {} 对象拼接的数组。
      - 'jsonblock': 只提取 ```json 代码块中的内容。
      - 'array': 只提取第一个独立的 [] JSON 数组。
      - 'objects': 提取所有顶层的 {} JSON 对象并组成一个数组。
    """

    def find_json_block():
        """使用正则表达式安全地提取 json 代码块"""
        # 使用非贪婪模式 (.*?) 来匹配最近的 ```
        match = re.search(r'```json\s*([\s\S]*?)\s*```', text)
        if match:
            content = match.group(1).strip()
            try:
                # 验证提取的是否是合法的JSON
                json.loads(content)
                return content
            except json.JSONDecodeError:
                return None
        return None

    def find_array():
        """查找第一个合法的 [] 数组"""
        # 使用栈平衡来查找完整且合法的JSON数组
        start_char, end_char = '[', ']'
        
        # 从头开始查找第一个起始字符
        try:
            start_index = text.find(start_char)
        except ValueError:
            start_index = -1
            
        while start_index != -1:
            stack = 0
            in_string = False
            
            # 从找到的起始字符开始遍历
            for i in range(start_index, len(text)):
                char = text[i]

                # 切换字符串状态，忽略字符串中的特殊字符
                if char == '"' and (i == 0 or text[i-1] != '\\'):
                    in_string = not in_string
                
                if in_string:
                    continue

                if char == start_char:
                    stack += 1
                elif char == end_char:
                    stack -= 1
                
                if stack == 0:
                    # 找到了一个完整的、闭合的结构
                    potential_json = text[start_index : i + 1]
                    try:
                        # 验证提取的是否是合法的JSON
                        json.loads(potential_json)
                        return potential_json
                    except json.JSONDecodeError:
                        # 如果不是合法的JSON，跳出内层循环
                        # 从当前闭合结构的下一个位置继续寻找新的起始点
                        break
            
            # 从当前 start_index 的后一个位置继续查找新的起始字符
            try:
                start_index = text.find(start_char, start_index + 1)
            except ValueError:
                start_index = -1

        return None


    def find_objects():
        """查找所有顶层对象并拼接成数组"""
        objs = []
        i = 0
        in_string = False
        
        while i < len(text):
            # 忽略字符串中的 '{'
            char = text[i]
            if char == '"' and (i == 0 or text[i-1] != '\\'):
                in_string = not in_string

            if text[i] == '{' and not in_string:
                start_idx = i
                stack = 1
                obj_in_string = False
                j = i + 1
                while j < len(text):
                    char_j = text[j]
                    if char_j == '"' and (j == 0 or text[j-1] != '\\'):
                        obj_in_string = not obj_in_string

                    if not obj_in_string:
                        if char_j == '{':
                            stack += 1
                        elif char_j == '}':
                            stack -= 1
                    
                    if stack == 0:
                        obj_str = text[start_idx:j+1]
                        try:
                            # 验证是否为合法JSON对象
                            json.loads(obj_str)
                            objs.append(obj_str)
                        except json.JSONDecodeError:
                            pass # 不是合法的，忽略
                        i = j # 从当前对象后继续搜索
                        break
                    j += 1
            i += 1
            
        if objs: # 只要找到至少一个对象
            return f"[{','.join(objs)}]"
        return None

    # --- 主逻辑 ---
    if mode == 'jsonblock':
        return find_json_block()
    if mode == 'array':
        return find_array()
    if mode == 'objects':
        return find_objects()
    
    # 'auto' 模式逻辑
    # 按优先级尝试
    result = find_json_block()
    if result is not None:
        return result
        
    result = find_array()
    if result is not None:
        return result
        
    result = find_objects()
    if result is not None:
        return result

    return None


if __name__ == '__main__':
    # 路径可根据实际情况调整
    chunk_json_path = "./all_pdf_page_chunks.json"
    rag = SimpleRAG(chunk_json_path)
    rag.setup()

    # 控制测试时读取的题目数量，默认只随机抽取10个，实际跑全部时设为None
    TEST_SAMPLE_NUM = 10  # 设置为None则全部跑
    FILL_UNANSWERED = True  # 未回答的也输出默认内容

    # 批量评测脚本：读取测试集，检索+大模型生成，输出结构化结果
    test_path = "./datas/test.json"
    if os.path.exists(test_path):
        with open(test_path, 'r', encoding='utf-8') as f:
            test_data = json.load(f)

        # 记录所有原始索引
        all_indices = list(range(len(test_data)))
        # 随机抽取部分题目用于测试
        selected_indices = all_indices
        if TEST_SAMPLE_NUM is not None and TEST_SAMPLE_NUM > 0:
            if len(test_data) > TEST_SAMPLE_NUM:
                selected_indices = sorted(random.sample(all_indices, TEST_SAMPLE_NUM))

        def process_one(idx):
            item = test_data[idx]
            question = item['question']
            tqdm.write(f"[{selected_indices.index(idx)+1}/{len(selected_indices)}] 正在处理: {question[:30]}...")
            result = rag.generate_answer(question, top_k=5)
            return idx, result

        results = []
        if selected_indices:
            with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
                results = list(tqdm(executor.map(process_one, selected_indices), total=len(selected_indices), desc='并发批量生成'))

        # 先输出一份未过滤的原始结果（含 idx）
        raw_out_path = "./rag_top1_pred_raw.json"
        with open(raw_out_path, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f'已输出原始未过滤结果到: {raw_out_path}')

        # 只保留结果部分，并去除 retrieval_chunks 字段
        idx2result = {idx: {k: v for k, v in r.items() if k != 'retrieval_chunks'} for idx, r in results}
        filtered_results = []
        for idx, item in enumerate(test_data):
            if idx in idx2result:
                filtered_results.append(idx2result[idx])
            elif FILL_UNANSWERED:
                # 未被回答的，补默认内容
                filtered_results.append({
                    "question": item.get("question", ""),
                    "answer": "",
                    "filename": "",
                    "page": "",
                })
        # 输出结构化结果到json
        out_path = "./rag_top1_pred.json"
        with open(out_path, 'w', encoding='utf-8') as f:
            json.dump(filtered_results, f, ensure_ascii=False, indent=2)
        print(f'已输出结构化检索+大模型生成结果到: {out_path}')
    else:
        print("datas/test.json 不存在")