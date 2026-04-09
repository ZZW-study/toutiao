# -*- coding: utf-8 -*-
"""统一限流调度器。

整合所有限流逻辑，提供统一的限流入口。
执行流程：黑名单检查 → 滑动窗口防刷 → 分布式限流 → Redis异常本地降级
"""


from fastapi.requests import Request
from typing import Optional

from configs.settings import get_settings
from utils.logger import get_logger
from middlewares.rate_limit.config import RateLimitConfig, RateLimitResult, RateLimitDimension
from middlewares.rate_limit.token_bucket import LocalTokenBucket
from middlewares.rate_limit.redis_limit import RedisRateLimit


settings = get_settings()
logger = get_logger(name="RateLimiter")


# 统一限流调度器（串联所有限流逻辑，核心入口类）
# 完整执行流程：黑名单检查 → 滑动窗口防刷 → 分布式限流 → Redis异常本地降级
class UnifiedRateLimiter:
    """
    统一限流器
    作用：整合所有限流规则，业务层只需调用此类，无需关心底层实现
    """
    def __init__(self, config: Optional[RateLimitConfig] = None):
        self.cfg = config or RateLimitConfig()

    def _get_identifier(self, request: Request) -> str:
        """
        从FastAPI请求对象中生成唯一限流标识
        支持三种模式：IP限流 / 用户ID限流 / IP+用户组合限流
        :param request: FastAPI Request请求对象
        :return: 唯一限流标识字符串
        """
        # 获取客户端IP：兼容无client属性的异常情况
        ip = request.client.host if hasattr(request, "client") else "unknown"
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

    async def check(self, request: Request) -> RateLimitResult:
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
        exceeded, count = await RedisRateLimit.anti_spam_check(ident)
        if exceeded:
            await RedisRateLimit.add_to_blacklist(ident)
            return RateLimitResult(
                allowed=False,
                reason=f"请求频率过高({count}次)，已自动封禁"
            )

        # 3.分布式令牌桶限流，检查令牌是否充足
        limit_result = await RedisRateLimit.token_limit(ident, self.cfg)
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


# 全局限流器实例
unified_limiter = UnifiedRateLimiter()
