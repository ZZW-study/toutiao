# -*- coding: utf-8 -*-
"""本地令牌桶实现。

高性能本地限流，使用内存存储令牌状态。
支持 LRU 策略清理旧实例，防止内存泄漏。
"""


import time
import asyncio
from typing import Dict

from utils.logger import get_logger
from middlewares.rate_limit.config import RateLimitConfig, RateLimitResult


logger = get_logger(name="LocalTokenBucket")


class LocalTokenBucket:
    """
    本地令牌桶实现

    特性：
    - 异步安全：每个桶有独立的锁
    - LRU 清理：实例数超阈值自动清理旧实例
    - 自动补充：根据时间差自动计算令牌补充
    """
    _instances: Dict[str, "LocalTokenBucket"] = {}
    _lock: asyncio.Lock = asyncio.Lock()
    _max_instances: int = 10000  # 最大实例数，防止内存泄漏

    def __init__(self, capacity: int = None, rate: float = None):
        self.capacity = capacity or RateLimitConfig.capacity
        self.rate = rate or RateLimitConfig.rate
        self.tokens = float(self.capacity)
        self.last_refill_time = time.time()
        self._refill_lock = asyncio.Lock()  # 每个桶自己的锁，防止竞态条件

    @classmethod
    async def get_instance(cls, key: str, capacity: int = None, rate: float = None) -> "LocalTokenBucket":
        """
        获取或创建令牌桶实例（线程安全）
        使用LRU策略：当实例数超过阈值时，清理最旧的实例
        """
        async with cls._lock:
            if key not in cls._instances:
                # 检查是否需要清理（防止内存泄漏）
                if len(cls._instances) >= cls._max_instances:
                    # 清理一半的最旧实例
                    keys_to_remove = list(cls._instances.keys())[:cls._max_instances // 2]
                    for k in keys_to_remove:
                        del cls._instances[k]
                    logger.warning(f"[本地令牌桶] 已清理 {len(keys_to_remove)} 个旧实例")

                cls._instances[key] = cls(capacity, rate)
            return cls._instances[key]

    async def _refill(self) -> None:
        """补充令牌（异步安全）"""
        async with self._refill_lock:
            now = time.time()
            elapsed_time = now - self.last_refill_time
            new_tokens = elapsed_time * self.rate
            self.tokens = min(self.tokens + new_tokens, self.capacity)
            self.last_refill_time = now

    async def try_consume(self, tokens: float = 1.0) -> RateLimitResult:
        """尝试消费令牌（异步安全）"""
        await self._refill()
        if self.tokens >= tokens:
            self.tokens -= tokens
            return RateLimitResult(allowed=True, remaining_tokens=self.tokens)
        need_tokens = tokens - self.tokens
        wait_time = need_tokens / self.rate
        return RateLimitResult(
            allowed=False,
            retry_after=wait_time,
            remaining_tokens=self.tokens,
            reason="本地令牌不足，请求频繁"
        )
