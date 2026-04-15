# -*- coding: utf-8 -*-
"""
令牌桶算法限流与接口防刷系统

兼容导入模块 - 所有实现已迁移到 rate_limit 子包

本文件保留用于向后兼容，新代码请直接使用：
    from middlewares.rate_limit import rate_limit, rate_limit_dependency
"""

# 从新模块导出所有公共接口
from middlewares.rate_limit import (  # 从 middlewares.rate_limit 模块导入当前文件后续要用到的对象
    # 配置类
    RateLimitDimension,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    RateLimitConfig,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    RateLimitResult,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    # 本地令牌桶
    LocalTokenBucket,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    # Redis 限流
    RedisRateLimit,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    # 统一限流器
    UnifiedRateLimiter,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    unified_limiter,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    # 装饰器和依赖注入
    rate_limit,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    rate_limit_dependency,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    custom_rate_limit_handler,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
)  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级

__all__ = [  # 把右边计算出来的结果保存到 __all__ 变量中，方便后面的代码继续复用
    "RateLimitDimension",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    "RateLimitConfig",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    "RateLimitResult",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    "LocalTokenBucket",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    "RedisRateLimit",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    "UnifiedRateLimiter",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    "unified_limiter",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    "rate_limit",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    "rate_limit_dependency",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    "custom_rate_limit_handler",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
]  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
