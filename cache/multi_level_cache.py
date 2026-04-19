# -*- coding: utf-8 -*-
"""多级缓存协调器。

L1：本地进程内热点缓存，极低延迟
L2：Redis 共享缓存，跨进程复用
DB：最终数据源

读取顺序：L1 -> L2 -> DB
"""

from __future__ import annotations

from functools import wraps
from threading import RLock
from typing import Any, Callable, Coroutine, Optional, TypeVar

from cache.local_cache import local_cache
from cache.redis_cache import CacheUtil, cache, generate_cache_key, logic_cache
from utils.logger import get_logger
from utils.singleflight import singleflight

# 空值缓存过期时间（秒），防止缓存穿透
NULL_CACHE_EXPIRE_SECONDS = 300

T = TypeVar("T")
logger = get_logger(name="MultiLevelCache")


class MultiLevelCache:
    """多级缓存核心协调类，单例模式。"""

    _instance_lock: RLock = RLock()
    _instance: Optional["MultiLevelCache"] = None

    def __new__(cls, *args: Any, **kwargs: Any) -> "MultiLevelCache":
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance.l1 = local_cache
                cls._instance.l2 = CacheUtil
        return cls._instance

    async def get(
        self,
        key: str,
        db_func: Optional[Callable[..., Coroutine[Any, Any, T]]] = None,
        *db_args: Any,
        **db_kwargs: Any,
    ) -> Optional[T]:
        """统一读取入口，顺序：L1 -> L2 -> DB。"""
        # 查 L1
        local_entry = self.l1.get_entry(key)
        if local_entry.hit:
            return local_entry.value

        # 查 L2
        redis_entry = await self.l2.get_entry(key)
        if redis_entry.hit:
            # 回填 L1
            self.l1.set(
                key,
                redis_entry.value,
                ttl=NULL_CACHE_EXPIRE_SECONDS if redis_entry.value is None else None,
            )
            return redis_entry.value

        if db_func is None:
            return None

        async def load_and_fill() -> Optional[T]:
            """回源 DB 并填充两级缓存。"""
            # SingleFlight 内双检
            second_local = self.l1.get_entry(key)
            if second_local.hit:
                return second_local.value

            second_redis = await self.l2.get_entry(key)
            if second_redis.hit:
                self.l1.set(
                    key,
                    second_redis.value,
                    ttl=NULL_CACHE_EXPIRE_SECONDS if second_redis.value is None else None,
                )
                return second_redis.value

            # 回源 DB
            db_value = await db_func(*db_args, **db_kwargs)
            if db_value is None:
                await self.l2.set(key, None, ex=NULL_CACHE_EXPIRE_SECONDS)
                self.l1.set(key, None, ttl=NULL_CACHE_EXPIRE_SECONDS)
                return None

            await self.l2.set(key, db_value)
            self.l1.set(key, db_value)
            return db_value

        return await singleflight.do(f"multi-cache:{key}", load_and_fill)

    async def delete(self, key: str) -> None:
        """删除两级缓存。"""
        await self.l2.delete(key)
        self.l1.delete(key)

    async def refresh(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """主动刷新两级缓存。"""
        await self.l2.set(key, value, ex=ttl)
        self.l1.set(
            key,
            value,
            ttl=NULL_CACHE_EXPIRE_SECONDS if value is None else ttl,
        )


multi_level_cache = MultiLevelCache()


def multi_cache(
    key_prefix: str,
    expire: int = 3600,
    hot: bool = False,
) -> Callable[[Callable[..., Coroutine[Any, Any, T]]], Callable[..., Coroutine[Any, Any, Optional[T]]]]:
    """业务层便捷装饰器。

    hot=True 使用 stale-while-revalidate 策略
    hot=False 使用标准读穿缓存
    """
    redis_decorator = logic_cache(key_prefix=key_prefix, expire_seconds=expire) if hot else cache(
        key_prefix=key_prefix,
        expire=expire,
    )

    def decorator(
        func: Callable[..., Coroutine[Any, Any, T]]
    ) -> Callable[..., Coroutine[Any, Any, Optional[T]]]:
        redis_wrapped = redis_decorator(func)

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Optional[T]:
            cache_key = generate_cache_key(key_prefix, args, kwargs)

            # 先查 L1
            local_entry = multi_level_cache.l1.get_entry(cache_key)
            if local_entry.hit:
                return local_entry.value

            # L1 未命中走 Redis 层
            result = await redis_wrapped(*args, **kwargs)
            multi_level_cache.l1.set(
                cache_key,
                result,
                ttl=NULL_CACHE_EXPIRE_SECONDS if result is None else expire,
            )
            return result

        return wrapper

    return decorator


# 兼容旧拼写
MutiLevelCache = MultiLevelCache
