# -*- coding: utf-8 -*-
"""限流模块统一导出。

本模块提供令牌桶限流和接口防刷功能。

主要导出：
- 装饰器：rate_limit（用于单个接口限流）
- 依赖注入：rate_limit_dependency（用于全局/路由组限流）
- 配置类：RateLimitConfig, RateLimitDimension, RateLimitResult
- 限流器：UnifiedRateLimiter, unified_limiter
"""

from middlewares.rate_limit.config import (  # 从 middlewares.rate_limit.config 模块导入当前文件后续要用到的对象
    RateLimitDimension,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    RateLimitConfig,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    RateLimitIdentity,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    RateLimitResult,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
)  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
from middlewares.rate_limit.token_bucket import LocalTokenBucket  # 从 middlewares.rate_limit.token_bucket 模块导入当前文件后续要用到的对象
from middlewares.rate_limit.redis_limit import RedisRateLimit  # 从 middlewares.rate_limit.redis_limit 模块导入当前文件后续要用到的对象
from middlewares.rate_limit.limiter import UnifiedRateLimiter, unified_limiter  # 从 middlewares.rate_limit.limiter 模块导入当前文件后续要用到的对象
from middlewares.rate_limit.decorators import (  # 从 middlewares.rate_limit.decorators 模块导入当前文件后续要用到的对象
    rate_limit,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    rate_limit_dependency,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    custom_rate_limit_handler,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
)  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级

__all__ = [  # 把右边计算出来的结果保存到 __all__ 变量中，方便后面的代码继续复用
    # 配置类
    "RateLimitDimension",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    "RateLimitConfig",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    "RateLimitIdentity",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    "RateLimitResult",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    # 本地令牌桶
    "LocalTokenBucket",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    # Redis 限流
    "RedisRateLimit",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    # 统一限流器
    "UnifiedRateLimiter",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    "unified_limiter",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    # 装饰器和依赖注入
    "rate_limit",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    "rate_limit_dependency",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    "custom_rate_limit_handler",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
]  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
