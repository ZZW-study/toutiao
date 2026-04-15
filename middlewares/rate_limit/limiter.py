# -*- coding: utf-8 -*-
"""统一限流调度器。"""

from __future__ import annotations

from fastapi.requests import Request

from configs.settings import get_settings
from middlewares.rate_limit.config import (
    RateLimitConfig,
    RateLimitDimension,
    RateLimitIdentity,
    RateLimitResult,
)
from middlewares.rate_limit.redis_limit import RedisRateLimit
from middlewares.rate_limit.token_bucket import LocalTokenBucket
from utils.logger import get_logger

settings = get_settings()
logger = get_logger(name="RateLimiter")


class UnifiedRateLimiter:
    """统一限流入口。"""

    def __init__(self, config: RateLimitConfig | None = None) -> None:
        """初始化统一限流器，并确定当前要使用的限流配置。"""
        self.cfg = config or RateLimitConfig()

    def _get_client_ip(self, request: Request) -> str:
        """提取客户端 IP。

        先读反向代理常见头，再回退到 `request.client.host`。
        """

        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            return forwarded_for.split(",")[0].strip()

        real_ip = request.headers.get("X-Real-IP")
        if real_ip:
            return real_ip.strip()

        return request.client.host if request.client else "unknown"

    def _build_identity(self, request: Request) -> RateLimitIdentity:
        """根据请求和配置构造限流身份。"""

        ip = self._get_client_ip(request)
        user_id = getattr(request.state, "user_id", None)

        if self.cfg.dimension == RateLimitDimension.IP:
            return RateLimitIdentity(key=f"ip:{ip}", ip=ip, user_id=None, scope="ip")

        if self.cfg.dimension == RateLimitDimension.USER_ID:
            if user_id is not None:
                return RateLimitIdentity(
                    key=f"user:{user_id}",
                    ip=ip,
                    user_id=user_id,
                    scope="user",
                )
            return RateLimitIdentity(key=f"ip:{ip}", ip=ip, user_id=None, scope="ip")

        if user_id is not None:
            return RateLimitIdentity(
                key=f"user:{user_id}:ip:{ip}",
                ip=ip,
                user_id=user_id,
                scope="combined",
            )

        return RateLimitIdentity(key=f"ip:{ip}", ip=ip, user_id=None, scope="ip")

    async def check(self, request: Request) -> RateLimitResult:
        """执行完整限流流程。

        为了避免同一请求链路里被 dependency/middleware 重复执行，
        这里加入了请求级幂等保护。
        """

        if getattr(request.state, "_rate_limit_checked", False):
            return getattr(
                request.state,
                "_rate_limit_result",
                RateLimitResult(allowed=True),
            )

        identity = self._build_identity(request)

        try:
            if await RedisRateLimit.is_in_blacklist(identity.key):
                result = RateLimitResult(
                    allowed=False,
                    retry_after=float(settings.BLACKLIST_DURATION),
                    reason="已被临时封禁，请稍后再试",
                )
                request.state._rate_limit_checked = True
                request.state._rate_limit_result = result
                return result

            exceeded, count = await RedisRateLimit.anti_spam_check(identity)
            if exceeded:
                await RedisRateLimit.add_to_blacklist(identity.key)
                result = RateLimitResult(
                    allowed=False,
                    retry_after=float(settings.BLACKLIST_DURATION),
                    reason=f"请求频率过高（{count} 次），已自动封禁",
                )
                request.state._rate_limit_checked = True
                request.state._rate_limit_result = result
                return result

            result = await RedisRateLimit.token_limit(identity, self.cfg)
            if "Redis异常" in result.reason and settings.ENABLE_LOCAL_FALLBACK:
                logger.warning("Redis 限流不可用，启用本地令牌桶降级", identity=identity.key)
                bucket = await LocalTokenBucket.get_instance(
                    identity.key,
                    self.cfg.capacity,
                    self.cfg.rate,
                )
                result = await bucket.try_consume()

            request.state._rate_limit_checked = True
            request.state._rate_limit_result = result
            return result
        except Exception as exc:
            logger.warning("统一限流执行异常，降级放行", error=str(exc), exc_info=True)
            result = RateLimitResult(allowed=True, reason="限流服务异常，临时放行")
            request.state._rate_limit_checked = True
            request.state._rate_limit_result = result
            return result


unified_limiter = UnifiedRateLimiter()
