# -*- coding: utf-8 -*-
"""限流装饰器和依赖注入。

提供 FastAPI 接口集成方式：
1. 装饰器：为单个接口添加限流
2. 依赖注入：用于全局/路由组限流
"""


from fastapi.requests import Request
from fastapi import HTTPException, status
from fastapi.responses import JSONResponse
from typing import Callable, TypeVar, Coroutine, Any
from functools import wraps

from utils.logger import get_logger
from middlewares.rate_limit.config import RateLimitConfig, RateLimitDimension
from middlewares.rate_limit.limiter import UnifiedRateLimiter, unified_limiter


T = TypeVar("T")
logger = get_logger(name="RateLimitDecorator")


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
    return JSONResponse(
        status_code=429,
        content={
            "code": 429,
            "message": "请求过于频繁，请稍后再试",
            "detail": str(exc) if str(exc) else "Rate limit exceeded"
        }
    )
