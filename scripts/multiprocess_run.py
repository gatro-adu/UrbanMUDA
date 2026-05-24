import multiprocessing as mp
import time
import random
from functools import wraps
from typing import Callable, List, Any, Iterable, Tuple
from itertools import islice
import logging
import inspect
import asyncio
# import openai

from yaml.scanner import ScannerError
from yaml.parser import ParserError
# from pydantic_core import ValidationError

# 配置日志（建议外部配置，这里仅为示例）
# logger = logging.getLogger(__name__)

## 使用方法
# multiprocess_run(
#     task_func=main, 
#     inputs=topics[10:20], 
#     batch_size=1, # 轻任务小batch(负载均衡)、重任务大batch
#     num_processes=10
# )

def multiprocess_run(  # 每个进程内单线程运行
    *,
    task_func: Callable[[Any], List[Tuple[Any, Any, Any]]],
    inputs: List[Any],
    batch_size: int,
    num_processes: int = None,
    chunksize: int = 1,
    flatten_results: bool = True
) -> List[Tuple[Any, Any, Any]]:
    """
    使用多进程并行处理输入数据。

    参数:
        task_func: 处理单个输入的函数，返回一个 list of tuple (e.g., [(only_key, redis_key, content), ...])
        inputs: 输入数据列表
        batch_size: 每个子任务处理的输入数量（用于减少进程间通信开销）
        num_processes: 进程数，默认为 CPU 核心数
        chunksize: imap 的 chunksize，控制每次发送给进程的任务批次数量（提高吞吐）
        flatten_results: 是否将 batch 结果展平为一个大列表（默认 True）

    返回:
        所有 task_func 返回结果的列表（默认已展平）
    """
    if not inputs:
        return []

    if num_processes is None:
        num_processes = mp.cpu_count()

    utils = Utils(task_func)

    num_processes = min(num_processes, len(inputs))
    with mp.Pool(processes=num_processes) as pool:
        batches = Utils.batched_iter(inputs, batch_size)
        results_iter = pool.imap(utils.worker_process, batches, chunksize=chunksize)  # chunksize -> n*batchsize个input

        all_results = []
        for batch_result in results_iter:
            if flatten_results:
                all_results.extend(batch_result)
            else:
                all_results.append(batch_result)

    return all_results

async def multiprocess_arun(  # 每个进程内单线程运行
    *,
    task_func: Callable[[Any], List[Tuple[Any, Any, Any]]],
    inputs: List[Any],
    batch_size: int,
    num_processes: int = None,
    chunksize: int = 1,
    flatten_results: bool = True
) -> List[Tuple[Any, Any, Any]]:
    if not inputs:
        return []
    if num_processes is None:
        num_processes = mp.cpu_count()
    utils = Utils(task_func)
    num_processes = min(num_processes, len(inputs))
    with mp.Pool(processes=num_processes) as pool:
        batches = Utils.batched_iter(inputs, batch_size)
        results_iter = pool.imap(utils.worker_process, batches, chunksize=chunksize)  # chunksize -> n*batchsize个input
        all_results = []
        for batch_result in results_iter:
            if flatten_results:
                all_results.extend(batch_result)
            else:
                all_results.append(batch_result)
    return all_results


class MultiProcessRunner:
    def __init__(
        self,
        *,
        task_func: Callable[[Any], List[Tuple[Any, Any, Any]]],
        num_processes: int = None,
    ):
        """
        初始化并创建进程池（只做一次）
        """
        if num_processes is None:
            num_processes = mp.cpu_count()

        self.task_func = task_func
        self.num_processes = num_processes
        self._pool = mp.Pool(processes=num_processes)

        # ⚠️ utils 必须在主进程创建，但 worker 方法是可 pickle 的
        self._utils = Utils(task_func)

        self._closed = False

    def run(
        self,
        *,
        inputs: List[Any],
        batch_size: int,
        chunksize: int = 1,
        flatten_results: bool = True,
    ) -> List[Tuple[Any, Any, Any]]:
        if self._closed:
            raise RuntimeError("Process pool already closed")

        if not inputs:
            return []

        batches = Utils.batched_iter(inputs, batch_size)

        results_iter = self._pool.imap(
            self._utils.worker_process,
            batches,
            chunksize=chunksize,
        )

        all_results = []
        for batch_result in results_iter:
            if flatten_results:
                all_results.extend(batch_result)
            else:
                all_results.append(batch_result)

        return all_results


class Utils:
    def __init__(self, task_func: Callable):
        self.task_func = task_func
        self.is_async = inspect.iscoroutinefunction(task_func)
    
    @retry_on_exception(max_retries=5, delay=0.5, exceptions=(
        ScannerError, 
        ParserError, 
        KeyError, 
        ValueError
    ))
    def worker_process(self, batch: List[Any]) -> List[Tuple[Any, Any, Any]]:
        """子进程执行函数：处理一批输入"""
        results = []
        for item in batch:  # 应该只有一个item
            try:
                res = self.task_from_single(item)
                if res is not None:
                    results.append(res)
            except Exception as e:
                print('-'*100)
                print(f"Error processing item {item}: ")
                # logger.error(f"Error processing item {item}: {e}", exc_info=True)
                raise
                # 可选择继续或抛出异常，这里选择记录并跳过
        return results
    
    def task_from_single(self, single_input: Any) -> List[Tuple[Any, Any, Any]]:
        """包装 task_func，便于单独测试或替换"""
        if self.is_async:
            # 在子进程中运行异步函数
            return asyncio.run(self.task_func(**single_input))
        else:
            # 同步函数直接调用
            return self.task_func(**single_input)
        # return self.task_func(single_input)
    
    @staticmethod
    def batched_iter(iterable: Iterable[Any], batch_size: int) -> Iterable[List[Any]]:
        """将可迭代对象按批次切分"""
        if batch_size <= 0:
            raise ValueError("batch_size must be a positive integer")
        it = iter(iterable)
        while True:
            batch = list(islice(it, batch_size))
            if not batch:
                break
            yield batch

def retry_on_exception(max_retries=3, delay=1, backoff=2, exceptions=(Exception,)):
    """
    装饰器：在函数抛出指定异常时自动重试
    """
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            retries = 0
            current_delay = delay
            while retries <= max_retries:
                try:
                    
                    return func(*args, **kwargs), retries
                except exceptions as e:
                    retries += 1
                    if retries > max_retries:
                        print(f"报错参数: \n\nargs: {args}\n\nkwargs: {kwargs} after error: {e}")
                        raise  # 超过最大重试次数，抛出异常
                    print(f"Retry {retries}/{max_retries} after error: {e}")
                    time.sleep(current_delay + random.uniform(0, 0.1))  # 防止惊群
                    current_delay *= backoff
            return None  # This line should not be reached
        return wrapper
    return decorator

if __name__ == "__main__":
    print('哈哈哈')