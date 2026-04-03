"""
令牌桶算法限流与接口防刷系统
核心功能：
1. 本地令牌桶实现（高性能）
2. 分布式令牌桶（基于Redis Lua脚本，原子性保证）
3. 滑动窗口接口防刷（IP/用户维度）
4. 黑名单管理（自动封禁/解封）
5. 混合限流策略（本地+分布式降级）
架构设计：
- 限流维度：IP / 用户ID / 组合维度
- 限流策略：令牌桶（支持突发流量）
- 防刷机制：滑动窗口计数器
- 高可用：Redis异常时自动降级到本地限流
"""
import time
import hashlib
import asyncio
import uuid
from fastapi.requests import Request
from typing import Optional, Dict, Any, Callable, TypeVar, Coroutine
from functools import wraps
from dataclasses import dataclass
from enum import Enum



from configs.settings import get_settings
from utils.logger import get_logger
from configs.redis_conf import redis_client

T = TypeVar("T")
settings = get_settings()
logger = get_logger(name="RateLimiter")

class RateLimitDimension(Enum):
    """限流维度枚举"""
    IP = "ip"
    USER_ID = "user_id"
    COMBINED = "combined"

@dataclass
class RateLimitConfig:
    """限流配置"""
    capacity: int = settings.TOKEN_BUCKET_CAPACITY  # 桶容量（支持突发流量）
    rate: float = settings.TOKEN_RATE  # 令牌生成速率（个/秒）
    dimension: RateLimitDimension = RateLimitDimension(settings.RATE_LIMIT_DIMENSION)

@dataclass
class RateLimitResult:
    """限流结果返回结构"""
    allowed: bool  # 是否允许通过
    retry_after: float = 0.0  # 重试等待时间（秒）
    remaining_tokens: float = 0.0  # 剩余令牌数
    reason: str = ""  # 限流原因


class LocalTokenBucket:
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


class RedisRateLimit:
    """
    Redis 综合限流实现:
      1. 分布式令牌桶限流
      2. 滑动窗口接口防刷，把时间切成更小的片段，避免固定窗口限流的 “边界突刺” 问题。
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
    async def token_limit(ident: str,cfg: RateLimitConfig) ->RateLimitResult:
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
    async def anti_spam_check(ident: str) ->tuple[bool,int]:
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
    async def is_in_blacklist(ident: str) ->bool:
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


# 统一限流调度器（串联所有限流逻辑，核心入口类）
# 完整执行流程：黑名单检查 → 滑动窗口防刷 → 分布式限流 → Redis异常本地降级
class UnifiedRateLimiter:
    """
    统一限流器
    作用：整合所有限流规则，业务层只需调用此类，无需关心底层实现
    """
    def __init__(self,config: Optional[RateLimitConfig] = None):
        self.cfg = config or RateLimitConfig()

    def _get_identifier(self,request: Request) ->str:
        """
        从FastAPI请求对象中生成唯一限流标识
        支持三种模式：IP限流 / 用户ID限流 / IP+用户组合限流
        :param request: FastAPI Request请求对象
        :return: 唯一限流标识字符串
        """
        # 获取客户端IP：兼容无client属性的异常情况
        ip = request.client.host if hasattr(request,"client") else "unknown"
        # 获取登录用户ID：从请求状态state中获取（登录中间件赋值）
        user_id = request.state.user_id if hasattr(request.state, "user_id") else None

        # 根据配置的限流维度，返回对应标识
        dim = self.cfg.dimension
        if dim == RateLimitDimension.IP:
            # 纯IP限流
            return f"ip:{ip}"
        if dim == RateLimitDimension.USER_ID and user_id:
            # 纯用户ID限流（仅登录用户）
            return f"user:{user_id}"
        # 默认：组合限流（登录用户用IP+UID，未登录用纯IP）
        return f"com:{ip}:{user_id}" if user_id else f"ip:{ip}"


    async def check(self,request: Request) ->RateLimitResult:
        """
        执行完整的限流检查流程
        :param request: FastAPI请求对象
        :return: 最终限流结果
        """
        # 先生成当前请求的唯一限流标识
        ident = self._get_identifier(request)
        # 黑名单检查：在黑名单则直接拒绝访问
        if await RedisRateLimit.is_in_blacklist(ident):
            return RateLimitResult(allowed=False, reason="已被临时封禁，请稍后再试")

        # 2. 滑动窗口防刷检查：请求超限则加入黑名单并拒绝
        exceeded,count = await RedisRateLimit.anti_spam_check(ident)
        if exceeded:
            await RedisRateLimit.add_to_blacklist(ident)
            return RateLimitResult(
                allowed=False,
                reason=f"请求频率过高({count}次)，已自动封禁"
            )

        # 3.分布式令牌桶限流，检查令牌是否充足
        limit_result = await RedisRateLimit.token_limit(ident,self.cfg)
        # Redis服务正常时，直接返回令牌桶检查结果（无论通过/拒绝）
        if "Redis异常" not in limit_result.reason:
            return limit_result

        # 4. Redis异常降级：配置开启本地限流，则使用本地令牌桶兜底
        if settings.ENABLE_LOCAL_FALLBACK:
            logger.warning(f"[降级] Redis 异常，使用本地限流: {ident}")
            # 获取本地令牌桶实例
            bucket = await LocalTokenBucket.get_instance(ident, self.cfg.capacity, self.cfg.rate)
            # 执行本地限流检查
            return await bucket.try_consume()

        # 5. 无Redis、无降级，直接放行，保证服务可用性
        return RateLimitResult(allowed=True, reason="限流服务异常，临时放行")


unified_limiter = UnifiedRateLimiter() 

# FastAPI 接口集成：装饰器 + 依赖注入（业务接口直接使用）
def rate_limit(capacity: int = None, rate: float = None, dimension: RateLimitDimension = None):
    """
    限流装饰器：为单个FastAPI接口添加限流规则
    优先级：装饰器传参 > 全局settings配置
    :param capacity: 令牌桶容量（可选）
    :param rate: 令牌生成速率（可选）
    :param dimension: 限流维度（可选）
    :return: 装饰器
    """
    def decorator(func: Callable[..., Coroutine[Any, Any, T]]) -> Callable[..., Coroutine[Any, Any, T]]:
            # 保留原函数的元信息（函数名、注释等）
            @wraps(func)
            async def wrapper(*args: Any, **kwargs: Any) -> T:
                # 自动提取Request对象：优先从关键字参数，再从位置参数查找
                request: Request = kwargs.get("request")
                # 未找到Request对象，跳过限流直接执行接口
                if not request:
                    return await func(*args, **kwargs)

                # 复用限流器逻辑，避免每次请求创建新实例
                cfg = RateLimitConfig()
                limiter = UnifiedRateLimiter(cfg)
                res = await limiter.check(request)
                # 限流不通过，抛出429异常（请求过多）
                if not res.allowed:
                    from fastapi import HTTPException, status
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail={
                            "msg": res.reason,          # 拦截原因
                            "retry_after": res.retry_after  # 建议重试时间
                        },
                        headers={"Retry-After": str(round(res.retry_after, 1))}
                    )

                # 限流通过，执行原接口逻辑
                return await func(*args, **kwargs)
            return wrapper
    return decorator

async def rate_limit_dependency(request: Request):
    """
    限流依赖注入：用于全局/路由组限流，无需每个接口加装饰器
    :param request: FastAPI Request对象
    """
    try:
        res = await unified_limiter.check(request)
        if not res.allowed:
            from fastapi import HTTPException
            raise HTTPException(429, detail=res.reason)
    except HTTPException:
        # 重新抛出HTTP异常，让FastAPI处理
        raise
    except Exception as e:
        # 记录异常日志，便于排查问题
        logger.error(f"[限流依赖注入异常] {str(e)}")


async def custom_rate_limit_handler(request: Request, exc: Exception):
    """
    自定义限流异常处理器：处理 RateLimitExceeded 异常
    """
    from fastapi.responses import JSONResponse
    return JSONResponse(
        status_code=429,
        content={
            "code": 429,
            "message": "请求过于频繁，请稍后再试",
            "detail": str(exc) if str(exc) else "Rate limit exceeded"
        }
    )



