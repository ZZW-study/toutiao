# -*- coding: utf-8 -*-
"""Redis 分布式限流实现。

包含：
1. 分布式令牌桶限流（Lua 脚本实现）
2. 滑动窗口接口防刷
3. 黑名单自动封禁

全部使用 Lua 脚本保证原子性。
"""


import time
import hashlib
import uuid

from configs.settings import get_settings
from utils.logger import get_logger
from configs.redis_conf import redis_client
from middlewares.rate_limit.config import RateLimitConfig, RateLimitResult


settings = get_settings()
logger = get_logger(name="RedisRateLimit")


class RedisRateLimit:
    """
    Redis 综合限流实现:
      1. 分布式令牌桶限流
      2. 滑动窗口接口防刷，把时间切成更小的片段，避免固定窗口限流的 "边界突刺" 问题。
        把单位时间（比如 1 分钟）切分成多个小时间片（如每 10 秒一片）
        统计当前时刻往前推一个完整周期内所有小窗口的总请求数
        总请求数超过阈值就拒绝，否则放行
      3. 黑名单自动封禁
    全部使用 Lua 脚本保证原子性
    """
    # Lua 1：分布式令牌桶脚本
    LUA_TOKEN_BUCKET = """
    local key = KEYS[1]
    local capacity = tonumber(ARGV[1])
    local rate = tonumber(ARGV[2])
    local now_ms = tonumber(ARGV[3])

    -- 读取当前桶内令牌和最后更新时间
    local data = redis.call("HMGET", key, "tokens", "last_time")
    local tokens = tonumber(data[1]) or capacity
    local last_time = tonumber(data[2]) or now_ms

    -- 计算时间差，补充令牌
    local elapsed = (now_ms - last_time) / 1000
    tokens = math.min(capacity, tokens + elapsed * rate)

    -- 尝试获取 1 个令牌
    local allowed = 0
    if tokens >= 1 then
        allowed = 1
        tokens = tokens - 1
    end

    -- 保存新状态并设置过期时间（自动清理无用key）
    redis.call("HMSET", key, "tokens", tokens, "last_time", now_ms)
    redis.call("EXPIRE", key, 300)

    return {allowed, tokens}
"""
    # Lua 2：滑动窗口防刷脚本
    LUA_SLIDING_WINDOW = """
    local key = KEYS[1]
    local now = tonumber(ARGV[1])
    local window = tonumber(ARGV[2])
    local limit = tonumber(ARGV[3])
    local unique_id = ARGV[4]  -- 接收唯一ID，避免请求覆盖
    -- 移除窗口外的旧记录
    redis.call("ZREMRANGEBYSCORE", key, 0, now - window)
    -- 统计当前窗口内请求次数
    local count = redis.call("ZCARD", key)

    -- 超过阈值则拒绝，否则记录本次请求
    local pass = 0
    if count < limit then
        pass = 1
        -- 使用唯一ID替代random()，防止计数丢失
        redis.call("ZADD", key, now, unique_id)
    end

    redis.call("EXPIRE", key, window + 10)
    return {pass, count}
    """

    # 分布式令牌桶限流
    @staticmethod
    async def token_limit(ident: str, cfg: RateLimitConfig) -> RateLimitResult:
        """
        分布式令牌桶限流方法
        :param ident: 限流唯一标识（IP/用户ID/组合标识）
        :param cfg: 限流配置（桶容量、令牌速率等）
        :return: 限流检查结果对象
        """
        try:
            # 对限流标识进行MD5加密，避免特殊字符导致Redis Key异常
            hash_key = hashlib.md5(ident.encode()).hexdigest()
            redis_key = f"rl:token:{hash_key}"

            # 异步执行Lua脚本
            res = await redis_client.eval(
                RedisRateLimit.LUA_TOKEN_BUCKET,
                1,  # KEYS数量
                redis_key,
                cfg.capacity, cfg.rate, int(time.time() * 1000)
            )
            # 解析Lua脚本返回结果：第一个值为是否允许通过（0/1）
            allowed = bool(res[0])
            # 构造并返回限流结果对象
            return RateLimitResult(
                allowed=allowed,                     # 是否通过
                remaining_tokens=float(res[1]),       # 剩余令牌数
                reason="" if allowed else "分布式令牌不足"  # 拦截原因
            )
        except Exception as e:
            logger.error(f"[Redis令牌桶异常] {str(e)}")
            return RateLimitResult(allowed=True, reason="Redis异常，降级本地限流")

    # 滑动窗口接口防刷检查
    @staticmethod
    async def anti_spam_check(ident: str) -> tuple[bool, int]:
        """
        滑动窗口防刷：统计时间窗口内的请求次数，判断是否恶意刷接口
        :param ident: 限流唯一标识
        :return: 元组(是否超限, 当前窗口请求次数)
        """
        try:
            hash_key = hashlib.md5(ident.encode()).hexdigest()
            redis_key = f"rl:spam:{hash_key}"
            # 自动匹配限流阈值：用户标识用用户阈值，IP标识用IP阈值
            threshold = settings.USER_RATE_LIMIT if "user:" in ident else settings.IP_RATE_LIMIT
            # 从配置读取滑动窗口大小（秒）
            window = settings.SLIDING_WINDOW_SIZE
            unique_id = str(uuid.uuid4())

            # 执行Lua脚本：传入当前时间、窗口大小、请求阈值
            res = await redis_client.eval(
                RedisRateLimit.LUA_SLIDING_WINDOW,
                1,
                redis_key,
                int(time.time()), window, threshold, unique_id
            )

            # 解析结果：是否允许通过（0/1）、当前请求次数
            passed = bool(res[0])
            count = int(res[1])
            # 未通过 = 请求超限，返回(是否超限, 次数)
            return not passed, count
        except Exception as e:
            # 捕获异常，打印日志
            logger.error(f"[滑动窗口异常] {str(e)}")
            # 异常时默认放行，不影响正常用户访问
            return False, 0

    # 黑名单操作方法
    @staticmethod
    async def is_in_blacklist(ident: str) -> bool:
        """
        检查当前标识是否在黑名单中
        :param ident: 限流唯一标识
        :return: True=在黑名单，False=不在
        """
        # 标识加密+拼接黑名单专用Key
        hash_key = hashlib.md5(ident.encode()).hexdigest()
        # 检查Redis中是否存在该黑名单Key，存在=被封禁
        return await redis_client.exists(f"rl:black:{hash_key}") == 1

    @staticmethod
    async def add_to_blacklist(ident: str):
        """
        将恶意请求标识加入黑名单，自动过期
        :param ident: 限流唯一标识
        """
        # 标识加密+拼接黑名单Key
        hash_key = hashlib.md5(ident.encode()).hexdigest()
        key = f"rl:black:{hash_key}"
        # 写入Redis，设置配置中的封禁时长，值为flood（代表刷接口）
        await redis_client.setex(key, settings.BLACKLIST_DURATION, "flood")
        # 打印封禁日志
        logger.warning(f"[黑名单] 已封禁: {ident}")
