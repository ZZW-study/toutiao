"""本地缓存实现。

这一层只负责进程内短 TTL 热点缓存，不承担跨进程共享职责。
相比旧实现，这里重点修复了三个问题：

1. 读写都在同一把锁内完成，避免“检查存在后在锁外取值”的竞态。
2. 明确区分“未命中”和“命中了空值缓存”。
3. 不再额外起后台清理线程，而是在访问时顺手回收过期数据，降低复杂度。
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

    `hit=True` 表示当前 key 在缓存中存在，即使业务值为 `None` 也算命中。
    这样上层多级缓存就能区分“负缓存命中”和“完全未命中”。
    """

    hit: bool
    value: Any = None


@dataclass(slots=True)
class _StoredValue:
    """本地缓存内部存储结构。"""

    value: Any
    expire_at: float


class LocalLRUCache:
    """线程安全的本地 LRU + TTL 缓存。

    设计取舍：
    - 使用 `OrderedDict` 明确维护 LRU 顺序，逻辑直观，便于加中文注释。
    - TTL 按条目单独记录，兼容不同 key 传入不同 TTL。
    - 只在访问路径上做轻量清理，避免后台线程带来的生命周期问题。
    """

    def __init__(self, maxsize: int = 1000, ttl: int = 300) -> None:
        """初始化本地缓存的容量、默认 TTL、锁和统计字段。"""
        self.maxsize = maxsize
        self.ttl = ttl
        self._cache: "OrderedDict[Any, _StoredValue]" = OrderedDict()
        self._lock = RLock()
        self._empty_marker = EMPTY_CACHE_FLAG

        # 下面这组统计字段保留给排查缓存命中率使用。
        self.hit_count = 0
        self.miss_count = 0
        self.total_count = 0

        self.logger = get_logger(name="LocalLRUCache")

    def _now(self) -> float:
        """返回单调时钟时间，避免系统时间回拨影响过期判断。"""
        return time.monotonic()

    def _purge_expired_locked(self) -> None:
        """删除已过期的 key。

        这里必须在持锁状态下调用，否则会出现遍历和删除并发冲突。
        """

        now = self._now()
        expired_keys = [
            key for key, stored in self._cache.items() if stored.expire_at <= now
        ]
        for key in expired_keys:
            self._cache.pop(key, None)

    def _ensure_capacity_locked(self) -> None:
        """在写入后执行 LRU 淘汰。"""

        while len(self._cache) > self.maxsize:
            # `last=False` 表示弹出最久未使用的条目。
            evicted_key, _ = self._cache.popitem(last=False)
            self.logger.debug("本地缓存触发 LRU 淘汰", key=evicted_key)

    def get_entry(self, key: Any) -> LocalCacheEntry:
        """返回带命中状态的读取结果。"""

        with self._lock:
            self.total_count += 1
            self._purge_expired_locked()

            stored = self._cache.get(key)
            if stored is None:
                self.miss_count += 1
                return LocalCacheEntry(hit=False, value=None)

            # 命中后要移动到尾部，保持 LRU 顺序。
            self._cache.move_to_end(key)
            self.hit_count += 1

            if stored.value == self._empty_marker:
                return LocalCacheEntry(hit=True, value=None)
            return LocalCacheEntry(hit=True, value=stored.value)

    def get(self, key: Any) -> Optional[Any]:
        """兼容旧接口：只返回值，不返回命中状态。"""

        return self.get_entry(key).value

    def set(self, key: Any, value: Any, ttl: Optional[int] = None) -> None:
        """写入缓存。

        `None` 会被转换成专用空值标记，这样上层仍能识别这是一次有效的负缓存。
        """

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


# 全局单例：供多级缓存协调器复用。
local_cache = LocalLRUCache(maxsize=1000, ttl=300)
