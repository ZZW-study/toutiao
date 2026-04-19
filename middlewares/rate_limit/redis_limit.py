# -*- coding: utf-8 -*-
"""Redis 分布式限流实现。"""

from __future__ import annotations

import hashlib
import time
import uuid

from configs.redis import redis_client
from configs.settings import get_settings
from middlewares.rate_limit.config import RateLimitConfig, RateLimitIdentity, RateLimitResult
from utils.logger import get_logger

settings = get_settings()
logger = get_logger(name="RedisRateLimit")


class RedisRateLimit:
    """Redis 限流能力集合。

    当前同时提供：
    - 分布式令牌桶
    - 滑动窗口防刷
    - 黑名单封禁
    """

    # Lua 原子脚本：令牌桶——在 Redis 侧完成补充、扣减和写回，避免竞态
    LUA_TOKEN_BUCKET = """
    local key = KEYS[1]
    local capacity = tonumber(ARGV[1])
    local rate = tonumber(ARGV[2])
    local now_ms = tonumber(ARGV[3])

    local data = redis.call("HMGET", key, "tokens", "last_time")
    local tokens = tonumber(data[1]) or capacity
    local last_time = tonumber(data[2]) or now_ms

    local elapsed = (now_ms - last_time) / 1000
    tokens = math.min(capacity, tokens + elapsed * rate)

    local allowed = 0
    if tokens >= 1 then
        allowed = 1
        tokens = tokens - 1
    end

    redis.call("HMSET", key, "tokens", tokens, "last_time", now_ms)
    redis.call("EXPIRE", key, 300)

    return {allowed, tokens}
    """

    # Lua 原子脚本：滑动窗口——用 sorted set 记录请求时间戳，窗口外自动淘汰
    LUA_SLIDING_WINDOW = """
    local key = KEYS[1]
    local now = tonumber(ARGV[1])
    local window = tonumber(ARGV[2])
    local limit = tonumber(ARGV[3])
    local unique_id = ARGV[4]

    redis.call("ZREMRANGEBYSCORE", key, 0, now - window)
    local count = redis.call("ZCARD", key)

    local pass = 0
    if count < limit then
        pass = 1
        redis.call("ZADD", key, now, unique_id)
    end

    redis.call("EXPIRE", key, window + 10)
    return {pass, count}
    """

    @staticmethod
    def _hash_key(identity_key: str, prefix: str) -> str:
        """生成脱敏后的 Redis 限流键，避免直接暴露原始身份信息。"""
        return f"{prefix}:{hashlib.md5(identity_key.encode('utf-8')).hexdigest()}"

    @staticmethod
    async def token_limit(identity: RateLimitIdentity, cfg: RateLimitConfig) -> RateLimitResult:
        """执行分布式令牌桶限流。"""

        try:
            redis_key = RedisRateLimit._hash_key(identity.key, "rl:token")
            # 通过 Lua 脚本在 Redis 侧原子执行补充+扣减，保证分布式一致性
            result = await redis_client.eval(
                RedisRateLimit.LUA_TOKEN_BUCKET,
                1,
                redis_key,
                cfg.capacity,
                cfg.rate,
                int(time.time() * 1000),
            )

            allowed = bool(result[0])
            remaining_tokens = float(result[1])
            # 令牌不足时根据剩余缺口和补充速率推算最短等待时间
            retry_after = 0.0
            if not allowed and cfg.rate > 0:
                retry_after = max((1 - remaining_tokens) / cfg.rate, settings.RETRY_AFTER)

            return RateLimitResult(
                allowed=allowed,
                remaining_tokens=remaining_tokens,
                retry_after=retry_after,
                reason="" if allowed else "请求过于频繁，请稍后再试",
            )
        except Exception as exc:
            # Redis 执行失败时返回降级标记，上层可据此切换本地令牌桶
            logger.warning("Redis 令牌桶执行失败", error=str(exc), exc_info=True)
            return RateLimitResult(
                allowed=True,
                reason="Redis异常，降级本地限流",
            )

    @staticmethod
    async def anti_spam_check(identity: RateLimitIdentity) -> tuple[bool, int]:
        """执行滑动窗口防刷。"""

        try:
            redis_key = RedisRateLimit._hash_key(identity.key, "rl:spam")
            # 已登录用户使用更严格的阈值，匿名 IP 放宽
            threshold = settings.USER_RATE_LIMIT if identity.user_id is not None else settings.IP_RATE_LIMIT
            result = await redis_client.eval(
                RedisRateLimit.LUA_SLIDING_WINDOW,
                1,
                redis_key,
                int(time.time()),
                settings.SLIDING_WINDOW_SIZE,
                threshold,
                str(uuid.uuid4()),
            )
            passed = bool(result[0])
            count = int(result[1])
            # 返回 (是否超频, 窗口内请求数)
            return (not passed), count
        except Exception as exc:
            # 滑动窗口异常时不触发封禁，避免误判
            logger.warning("Redis 滑动窗口执行失败", error=str(exc), exc_info=True)
            return False, 0

    @staticmethod
    async def is_in_blacklist(identity_key: str) -> bool:
        """判断当前身份是否已经进入限流黑名单。"""
        key = RedisRateLimit._hash_key(identity_key, "rl:black")
        return await redis_client.exists(key) == 1

    @staticmethod
    async def add_to_blacklist(identity_key: str) -> None:
        """把当前身份写入黑名单，并设置自动过期时间。"""
        key = RedisRateLimit._hash_key(identity_key, "rl:black")
        await redis_client.setex(key, settings.BLACKLIST_DURATION, "flood")
        logger.warning("已将请求方加入限流黑名单", identity=identity_key)
