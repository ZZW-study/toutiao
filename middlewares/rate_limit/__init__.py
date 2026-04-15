# -*- coding: utf-8 -*-
"""限流模块统一导出。

本模块提供令牌桶限流和接口防刷功能。

主要导出：
- 装饰器：rate_limit（用于单个接口限流）
- 依赖注入：rate_limit_dependency（用于全局/路由组限流）
- 配置类：RateLimitConfig, RateLimitDimension, RateLimitResult
- 限流器：UnifiedRateLimiter, unified_limiter
"""

from middlewares.rate_limit.config import (
    RateLimitDimension,
    RateLimitConfig,
    RateLimitIdentity,
    RateLimitResult,
)
from middlewares.rate_limit.token_bucket import LocalTokenBucket
from middlewares.rate_limit.redis_limit import RedisRateLimit
from middlewares.rate_limit.limiter import UnifiedRateLimiter, unified_limiter
from middlewares.rate_limit.decorators import (
    rate_limit,
    rate_limit_dependency,
    custom_rate_limit_handler,
)

__all__ = [
    # 配置类
    "RateLimitDimension",
    "RateLimitConfig",
    "RateLimitIdentity",
    "RateLimitResult",
    # 本地令牌桶
    "LocalTokenBucket",
    # Redis 限流
    "RedisRateLimit",
    # 统一限流器
    "UnifiedRateLimiter",
    "unified_limiter",
    # 装饰器和依赖注入
    "rate_limit",
    "rate_limit_dependency",
    "custom_rate_limit_handler",
]
