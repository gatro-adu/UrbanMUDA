import json
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional

from langchain_core.chat_history import BaseChatMessageHistory
from langchain_core.messages import BaseMessage, messages_from_dict
from redis import Redis
from redis.exceptions import ConnectionError, ResponseError
from redisvl.exceptions import RedisSearchError  # type: ignore
from redisvl.index import SearchIndex  # type: ignore
from redisvl.query import CountQuery, FilterQuery, TextQuery  # type: ignore
from redisvl.query.filter import Tag  # type: ignore
from ulid import ULID

from langchain_redis.version import __full_lib_name__

logger = logging.getLogger(__name__)

def redis_db():
    def __init__(self, **kwargs):
        self.redis_client = kwargs.get('redis_client') or Redis.form_uri(kwargs.get('redis_uri', 'redis://localhost:6379'))
        self._create_search_index()
        