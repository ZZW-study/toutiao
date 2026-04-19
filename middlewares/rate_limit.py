# -*- coding: utf-8 -*-
"""Redis 令牌桶限流实现。"""

from __future__ import annotations
import time
from redis.asyncio import Redis


class RateLimitResult:
    """限流结果。"""
    def __init__(self, allowed: bool, remaining: float = 0.0, retry_after: float = 0.0):
        self.allowed = allowed          # 是否允许本次请求通过
        self.remaining = remaining      # 当前桶内剩余令牌数
        self.retry_after = retry_after  # 建议的重试等待时间（秒），仅当 allowed=False 时有意义


# Lua脚本：原子补充+扣减令牌
# 这是Lua脚本，会在 Redis 内部执行。
# 为什么用 Lua？因为 Redis 执行 Lua 脚本时，脚本中的多个 Redis 命令是原子的，不会被打断。
# 我们需要原子地：读取当前令牌数 → 计算补充了多少新令牌 → 判断能否扣减 → 保存新状态。
# KEYS[1] - 限流键名
# ARGV[1] - 桶容量 (capacity)
# ARGV[2] - 令牌生成速率 (rate, 个/秒)
# ARGV[3] - 当前时间戳（毫秒）
LUA_TOKEN_BUCKET = """
local key = KEYS[1]
local capacity = tonumber(ARGV[1])
local rate = tonumber(ARGV[2])
local now_ms = tonumber(ARGV[3])

-- 用的HAGET获取桶内现有令牌数和上次更新时间
local data = redis.call("HMGET", key, "tokens", "last_time")
local tokens = tonumber(data[1]) or capacity   -- 首次访问时，初始化为满桶
local last_time = tonumber(data[2]) or now_ms

-- 计算从上次更新到现在的令牌生成量，并更新桶内令牌数（不超过容量）
local elapsed = (now_ms - last_time) / 1000    -- 时间差（秒）
tokens = math.min(capacity, tokens + elapsed * rate)

-- 判断是否能放行（消耗1个令牌）
local allowed = 0
if tokens >= 1 then
    allowed = 1
    tokens = tokens - 1
end

-- "用的HMSET"保存新的令牌数和更新时间，并设置过期时间（300秒，避免无效key堆积）
redis.call("HMSET", key, "tokens", tokens, "last_time", now_ms)
redis.call("EXPIRE", key, 300)

-- 返回：是否允许（1/0）以及剩余令牌数
return {allowed, tokens}
"""


async def token_limit(
    redis: Redis,
    key: str,
    capacity: int = 10,
    rate: float = 5.0,
) -> RateLimitResult:
    """执行Redis令牌桶限流。

    使用Lua脚本保证原子性，实现平滑限流。

    Args:
        redis: Redis客户端实例
        key: 限流键（如用户ID、IP等）
        capacity: 令牌桶容量（最大突发请求数）
        rate: 令牌生成速率（个/秒）

    Returns:
        RateLimitResult 对象，包含是否允许、剩余令牌数、建议重试等待时间。
    """
    # 执行 Redis Lua 脚本进行原子性的令牌桶限流
    # 参数说明：
    #   LUA_TOKEN_BUCKET  : Lua 脚本源代码（字符串）
    #   1                 : 表示后续有 1 个参数属于 KEYS 数组
    #   key               : 限流键名，会被放入 KEYS[1]（例如 "rl:192.168.1.1"）
    #   capacity          : 桶容量，放入 ARGV[1]
    #   rate              : 令牌生成速率（个/秒），放入 ARGV[2]
    #   int(time.time() * 1000) : 当前毫秒时间戳，放入 ARGV[3]
    result = await redis.eval(
        LUA_TOKEN_BUCKET, 1, key, capacity, rate, int(time.time() * 1000)
)
    allowed = bool(result[0])          # 转为布尔值
    remaining = float(result[1])       # 剩余令牌数（可能为小数）
    
    # 若被限流，计算需要等待多久才能获得至少1个令牌
    retry_after = 0.0 if allowed else (1 - remaining) / rate

    return RateLimitResult(
        allowed=allowed,
        remaining=remaining,
        retry_after=retry_after,
    )