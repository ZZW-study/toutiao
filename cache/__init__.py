# -*- coding: utf-8 -*-
"""缓存模块统一导出。

本模块提供 L1 本地缓存、L2 Redis 缓存和多级缓存协调器的统一入口。
"""

from cache.constants import EMPTY_CACHE_FLAG
from cache.local_cache import LocalLRUCache, local_cache
from cache.redis_cache import CacheUtil, cache, logic_cache, generate_cache_key
from cache.multi_level_cache import MutiLevelCache, multi_level_cache, multi_cache

__all__ = [
    # 常量
    "EMPTY_CACHE_FLAG",
    # L1 本地缓存
    "LocalLRUCache",
    "local_cache",
    # L2 Redis 缓存
    "CacheUtil",
    "cache",
    "logic_cache",
    "generate_cache_key",
    # 多级缓存
    "MutiLevelCache",
    "multi_level_cache",
    "multi_cache",
]
