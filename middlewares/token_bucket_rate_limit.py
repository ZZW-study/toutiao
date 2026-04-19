# -*- coding: utf-8 -*-
"""
令牌桶算法限流与接口防刷系统

兼容导入模块 - 所有实现已迁移到 rate_limit 子包

本文件保留用于向后兼容，新代码请直接使用：
    from middlewares.rate_limit import rate_limit, rate_limit_dependency
"""

# 从新模块导出所有公共接口
from middlewares.rate_limit import (
    RateLimitDimension,
    RateLimitConfig,
    RateLimitResult,
    LocalTokenBucket,
    RedisRateLimit,
    UnifiedRateLimiter,
    unified_limiter,
    rate_limit,
    rate_limit_dependency,
    custom_rate_limit_handler,
)

__all__ = [
    "RateLimitDimension",
    "RateLimitConfig",
    "RateLimitResult",
    "LocalTokenBucket",
    "RedisRateLimit",
    "UnifiedRateLimiter",
    "unified_limiter",
    "rate_limit",
    "rate_limit_dependency",
    "custom_rate_limit_handler",
]
