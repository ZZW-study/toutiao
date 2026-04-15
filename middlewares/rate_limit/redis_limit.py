# -*- coding: utf-8 -*-
"""Redis 分布式限流实现。"""

from __future__ import annotations  # 开启延迟解析类型注解，避免前向引用在导入阶段就被过早求值

import hashlib  # 导入 hashlib 模块，给当前文件后面的逻辑使用
import time  # 导入 time 模块，给当前文件后面的逻辑使用
import uuid  # 导入 uuid 模块，给当前文件后面的逻辑使用

from configs.redis import redis_client  # 从 configs.redis 模块导入当前文件后续要用到的对象
from configs.settings import get_settings  # 从 configs.settings 模块导入当前文件后续要用到的对象
from middlewares.rate_limit.config import RateLimitConfig, RateLimitIdentity, RateLimitResult  # 从 middlewares.rate_limit.config 模块导入当前文件后续要用到的对象
from utils.logger import get_logger  # 从 utils.logger 模块导入当前文件后续要用到的对象

settings = get_settings()  # 把右边计算出来的结果保存到 settings 变量中，方便后面的代码继续复用
logger = get_logger(name="RedisRateLimit")  # 把右边计算出来的结果保存到 logger 变量中，方便后面的代码继续复用


class RedisRateLimit:  # 定义 RedisRateLimit 类，用来把这一块相关的状态和行为组织在一起
    """Redis 限流能力集合。

    当前同时提供：
    - 分布式令牌桶
    - 滑动窗口防刷
    - 黑名单封禁
    """

    # 这里开始定义 LUA_TOKEN_BUCKET 这一段多行字符串内容，后面连续几行都会被当成同一个文本值
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

    # 这里开始定义 LUA_SLIDING_WINDOW 这一段多行字符串内容，后面连续几行都会被当成同一个文本值
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

    @staticmethod  # 使用 staticmethod 装饰下面的函数或类，给它附加额外能力
    def _hash_key(identity_key: str, prefix: str) -> str:  # 定义函数 _hash_key，把一段可以复用的逻辑单独封装起来
        """生成脱敏后的 Redis 限流键，避免直接暴露原始身份信息。"""
        return f"{prefix}:{hashlib.md5(identity_key.encode('utf-8')).hexdigest()}"  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    @staticmethod  # 使用 staticmethod 装饰下面的函数或类，给它附加额外能力
    async def token_limit(identity: RateLimitIdentity, cfg: RateLimitConfig) -> RateLimitResult:  # 定义异步函数 token_limit，调用它时通常需要配合 await 使用
        """执行分布式令牌桶限流。"""

        try:  # 开始尝试执行可能出错的逻辑，如果报错就会转到下面的异常分支
            redis_key = RedisRateLimit._hash_key(identity.key, "rl:token")  # 把右边计算出来的结果保存到 redis_key 变量中，方便后面的代码继续复用
            result = await redis_client.eval(  # 把右边计算出来的结果保存到 result 变量中，方便后面的代码继续复用
                RedisRateLimit.LUA_TOKEN_BUCKET,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                1,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                redis_key,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                cfg.capacity,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                cfg.rate,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                int(time.time() * 1000),  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
            )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级

            allowed = bool(result[0])  # 把右边计算出来的结果保存到 allowed 变量中，方便后面的代码继续复用
            remaining_tokens = float(result[1])  # 把右边计算出来的结果保存到 remaining_tokens 变量中，方便后面的代码继续复用
            retry_after = 0.0  # 把右边计算出来的结果保存到 retry_after 变量中，方便后面的代码继续复用
            if not allowed and cfg.rate > 0:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                retry_after = max((1 - remaining_tokens) / cfg.rate, settings.RETRY_AFTER)  # 把右边计算出来的结果保存到 retry_after 变量中，方便后面的代码继续复用

            return RateLimitResult(  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
                allowed=allowed,  # 把右边计算出来的结果保存到 allowed 变量中，方便后面的代码继续复用
                remaining_tokens=remaining_tokens,  # 把右边计算出来的结果保存到 remaining_tokens 变量中，方便后面的代码继续复用
                retry_after=retry_after,  # 把右边计算出来的结果保存到 retry_after 变量中，方便后面的代码继续复用
                reason="" if allowed else "请求过于频繁，请稍后再试",  # 把右边计算出来的结果保存到 reason 变量中，方便后面的代码继续复用
            )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
        except Exception as exc:  # 如果上面 try 里的代码报错，就进入这个异常处理分支
            logger.warning("Redis 令牌桶执行失败", error=str(exc), exc_info=True)  # 记录一条日志，方便后续排查程序运行过程和定位问题
            return RateLimitResult(  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
                allowed=True,  # 把右边计算出来的结果保存到 allowed 变量中，方便后面的代码继续复用
                reason="Redis异常，降级本地限流",  # 把右边计算出来的结果保存到 reason 变量中，方便后面的代码继续复用
            )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级

    @staticmethod  # 使用 staticmethod 装饰下面的函数或类，给它附加额外能力
    async def anti_spam_check(identity: RateLimitIdentity) -> tuple[bool, int]:  # 定义异步函数 anti_spam_check，调用它时通常需要配合 await 使用
        """执行滑动窗口防刷。"""

        try:  # 开始尝试执行可能出错的逻辑，如果报错就会转到下面的异常分支
            redis_key = RedisRateLimit._hash_key(identity.key, "rl:spam")  # 把右边计算出来的结果保存到 redis_key 变量中，方便后面的代码继续复用
            threshold = settings.USER_RATE_LIMIT if identity.user_id is not None else settings.IP_RATE_LIMIT  # 把右边计算出来的结果保存到 threshold 变量中，方便后面的代码继续复用
            result = await redis_client.eval(  # 把右边计算出来的结果保存到 result 变量中，方便后面的代码继续复用
                RedisRateLimit.LUA_SLIDING_WINDOW,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                1,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                redis_key,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                int(time.time()),  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                settings.SLIDING_WINDOW_SIZE,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                threshold,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                str(uuid.uuid4()),  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
            )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
            passed = bool(result[0])  # 把右边计算出来的结果保存到 passed 变量中，方便后面的代码继续复用
            count = int(result[1])  # 把右边计算出来的结果保存到 count 变量中，方便后面的代码继续复用
            return (not passed), count  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
        except Exception as exc:  # 如果上面 try 里的代码报错，就进入这个异常处理分支
            logger.warning("Redis 滑动窗口执行失败", error=str(exc), exc_info=True)  # 记录一条日志，方便后续排查程序运行过程和定位问题
            return False, 0  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    @staticmethod  # 使用 staticmethod 装饰下面的函数或类，给它附加额外能力
    async def is_in_blacklist(identity_key: str) -> bool:  # 定义异步函数 is_in_blacklist，调用它时通常需要配合 await 使用
        """判断当前身份是否已经进入限流黑名单。"""
        key = RedisRateLimit._hash_key(identity_key, "rl:black")  # 把右边计算出来的结果保存到 key 变量中，方便后面的代码继续复用
        return await redis_client.exists(key) == 1  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    @staticmethod  # 使用 staticmethod 装饰下面的函数或类，给它附加额外能力
    async def add_to_blacklist(identity_key: str) -> None:  # 定义异步函数 add_to_blacklist，调用它时通常需要配合 await 使用
        """把当前身份写入黑名单，并设置自动过期时间。"""
        key = RedisRateLimit._hash_key(identity_key, "rl:black")  # 把右边计算出来的结果保存到 key 变量中，方便后面的代码继续复用
        await redis_client.setex(key, settings.BLACKLIST_DURATION, "flood")  # 等待这个异步操作完成，再继续执行后面的代码
        logger.warning("已将请求方加入限流黑名单", identity=identity_key)  # 记录一条日志，方便后续排查程序运行过程和定位问题
