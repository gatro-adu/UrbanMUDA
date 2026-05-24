# app/core/redis.py
from redis.asyncio import Redis, ConnectionPool
from contextlib import asynccontextmanager
from typing import AsyncGenerator

_redis_pool: ConnectionPool | None = None

async def init_redis(redis_url: str) -> None:
    """初始化 Redis 连接池"""
    global _redis_pool
    _redis_pool = ConnectionPool.from_url(
        redis_url,
        decode_responses=True,
        max_connections=20,  # 根据需求调整
        health_check_interval=30
    )

async def close_redis() -> None:
    """关闭连接池"""
    if _redis_pool:
        await _redis_pool.disconnect()

@asynccontextmanager
async def get_redis() -> AsyncGenerator[Redis, None]:
    """获取 Redis 客户端的上下文管理器"""
    if not _redis_pool:
        raise RuntimeError("Redis 连接池未初始化")
    
    redis = Redis(connection_pool=_redis_pool)
    try:
        yield redis
    finally:
        await redis.close()  # 归还连接到池


async def get_redis_client() -> AsyncGenerator[Redis, None]:
    """FastAPI 依赖项，用于注入 Redis 客户端"""
    async with get_redis() as client:  # 使用之前的上下文管理器
        yield client