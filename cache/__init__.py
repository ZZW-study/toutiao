# -*- coding: utf-8 -*-
"""缓存模块统一导出。"""

from cache.constants import EMPTY_CACHE_FLAG
from cache.local_cache import LocalLRUCache, local_cache
from cache.multi_level_cache import MutiLevelCache, MultiLevelCache, multi_cache, multi_level_cache
from cache.redis_cache import CacheUtil, cache, generate_cache_key, logic_cache

__all__ = [
    "EMPTY_CACHE_FLAG",
    "LocalLRUCache",
    "local_cache",
    "CacheUtil",
    "cache",
    "logic_cache",
    "generate_cache_key",
    "MultiLevelCache",
    "MutiLevelCache",
    "multi_level_cache",
    "multi_cache",
]
