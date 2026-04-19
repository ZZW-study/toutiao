# -*- coding: utf-8 -*-
"""本地缓存实现。

进程内短 TTL 热点缓存，使用 LRU + TTL 策略。
不承担跨进程共享职责，那是 Redis 的责任。
"""

from __future__ import annotations

import time
from collections import OrderedDict
from dataclasses import dataclass
from threading import RLock
from typing import Any, Dict, Optional

from cache.constants import EMPTY_CACHE_FLAG
from utils.logger import get_logger


@dataclass(slots=True)
class LocalCacheEntry:
    """本地缓存命中结果。

    hit=True 表示 key 存在，即使业务值为 None 也算命中（负缓存）。
    """

    hit: bool
    value: Any = None


@dataclass(slots=True)
class _StoredValue:
    """内部存储结构，包含值和过期时间。"""

    value: Any
    expire_at: float


class LocalLRUCache:
    """线程安全的本地 LRU + TTL 缓存。

    使用 OrderedDict 维护 LRU 顺序，访问时顺手清理过期数据。
    """

    def __init__(self, maxsize: int = 1000, ttl: int = 300) -> None:
        self.maxsize = maxsize  # 最大容量，超过时 LRU 淘汰
        self.ttl = ttl          # 默认过期时间（秒）
        self._cache: "OrderedDict[Any, _StoredValue]" = OrderedDict()  # 有序字典维护 LRU 顺序
        # 涉及到多个线程并发的内存数据操作、数据库数据操作，反正是跟数据有关的操作
        # 一定要锁，因为过程是这样的cpu先拿数据-->执行计算-->写入数据，很多更新的、删除的函数，其实是这三个过程。
        # 如果不能一气呵成，会出现超级多数据的问题。
        self._lock = RLock()  # 可重入锁：同一线程可多次 acquire 不会死锁，适合方法间嵌套调用，下面的代码有个多个嵌套调用，然后嵌套的调用的函数，都需要获得到，所有可重入锁非常重要。
        self._empty_marker = EMPTY_CACHE_FLAG  # 负缓存标记，区分 None 值和未命中

        # 统计字段
        self.hit_count = 0  # 命中次数
        self.miss_count = 0  # 未命中次数
        self.total_count = 0  # 总请求次数

        self.logger = get_logger(name="LocalLRUCache")

    def _now(self) -> float:
        """返回单调时钟时间，返回一个安全、可靠、只增不减的计时用时间戳，避免系统时间回拨影响。"""
        return time.monotonic()

    def _purge_expired_locked(self) -> None:
        """删除已过期的 key，必须在持锁状态下调用。"""
        now = self._now()
        expired_keys = [
            key for key, stored in self._cache.items() if stored.expire_at <= now
        ]
        for key in expired_keys:
            self._cache.pop(key, None)

    def _ensure_capacity_locked(self) -> None:
        """写入后执行 LRU 淘汰。"""
        while len(self._cache) > self.maxsize:
            self._cache.popitem(last=False)

    def get_entry(self, key: Any) -> LocalCacheEntry:
        """返回带命中状态的读取结果。"""
        with self._lock:
            self.total_count += 1
            self._purge_expired_locked()

            stored = self._cache.get(key)
            if stored is None:
                self.miss_count += 1
                return LocalCacheEntry(hit=False, value=None)

            self._cache.move_to_end(key)
            self.hit_count += 1

            if stored.value == self._empty_marker:
                return LocalCacheEntry(hit=True, value=None)
            return LocalCacheEntry(hit=True, value=stored.value)

    def set(self, key: Any, value: Any, ttl: Optional[int] = None) -> None:
        """写入缓存，None 转为空值标记以支持负缓存。"""
        if self.maxsize <= 0:
            self.logger.warning("本地缓存容量为 0，跳过写入", key=key)
            return

        ttl_seconds = ttl if ttl is not None else self.ttl
        expire_at = self._now() + max(ttl_seconds, 1)
        stored_value = self._empty_marker if value is None else value

        with self._lock:
            self._purge_expired_locked()
            self._cache[key] = _StoredValue(value=stored_value, expire_at=expire_at)
            self._cache.move_to_end(key)
            self._ensure_capacity_locked()

    def delete(self, key: Any) -> None:
        """删除单个缓存键。"""
        with self._lock:
            self._cache.pop(key, None)

    def touch(self, key: Any, ttl: Optional[int] = None) -> bool:
        """刷新某个 key 的过期时间。"""
        ttl_seconds = ttl if ttl is not None else self.ttl
        with self._lock:
            self._purge_expired_locked()
            stored = self._cache.get(key)
            if stored is None:
                return False
            stored.expire_at = self._now() + max(ttl_seconds, 1)
            self._cache.move_to_end(key)
            return True

    def clear(self) -> None:
        """清空本地缓存。"""
        with self._lock:
            self._cache.clear()

    def get_status(self) -> Dict[str, Any]:
        """返回基础监控信息。"""
        with self._lock:
            self._purge_expired_locked()
            hit_rate = (
                round(self.hit_count / self.total_count * 100, 2)
                if self.total_count
                else 0.0
            )
            return {
                "max_capacity": self.maxsize,
                "current_size": len(self._cache),
                "hit_count": self.hit_count,
                "miss_count": self.miss_count,
                "total_requests": self.total_count,
                "hit_rate": hit_rate,
                "default_ttl": self.ttl,
            }


# 全局单例
local_cache = LocalLRUCache(maxsize=1000, ttl=300)
