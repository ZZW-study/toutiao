# -*- coding: utf-8 -*-
"""限流装饰器与 FastAPI 依赖。"""

from __future__ import annotations

from functools import wraps
from typing import Any, Callable, Coroutine, TypeVar

from fastapi import Depends, HTTPException, status
from fastapi.requests import Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncSession

from configs.db import get_db
from middlewares.rate_limit.config import RateLimitConfig, RateLimitDimension
from middlewares.rate_limit.limiter import UnifiedRateLimiter, unified_limiter
from utils.auth import resolve_request_user_id
from utils.logger import get_logger

T = TypeVar("T")
logger = get_logger(name="RateLimit")


def _find_request(args: tuple[Any, ...], kwargs: dict[str, Any]) -> Request | None:
    """从位置参数或关键字参数中提取 Request。"""

    # 优先从关键字参数查找，再遍历位置参数
    request = kwargs.get("request")
    if isinstance(request, Request):
        return request

    for arg in args:
        if isinstance(arg, Request):
            return arg

    return None


def _build_config(
    capacity: int | None,
    rate: float | None,
    dimension: RateLimitDimension | None,
) -> RateLimitConfig:
    """把装饰器参数覆盖到默认配置上。"""

    # 仅在调用方显式传参时覆盖默认值
    base = RateLimitConfig()
    return RateLimitConfig(
        capacity=capacity if capacity is not None else base.capacity,
        rate=rate if rate is not None else base.rate,
        dimension=dimension if dimension is not None else base.dimension,
    )


def rate_limit(
    capacity: int | None = None,
    rate: float | None = None,
    dimension: RateLimitDimension | None = None,
) -> Callable[[Callable[..., Coroutine[Any, Any, T]]], Callable[..., Coroutine[Any, Any, T]]]:
    """为单个接口附加自定义限流规则。"""

    config = _build_config(capacity=capacity, rate=rate, dimension=dimension)
    limiter = UnifiedRateLimiter(config)

    def decorator(
        func: Callable[..., Coroutine[Any, Any, T]]
    ) -> Callable[..., Coroutine[Any, Any, T]]:
        """接收原函数并返回带限流校验的包装函数。"""

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> T:
            """在执行真实路由前，先完成请求级限流检查。"""
            request = _find_request(args, kwargs)
            if request is None:
                # 没有 Request 说明当前函数并不是 FastAPI 路由，直接放行。
                return await func(*args, **kwargs)

            # 限流不通过时抛出 429，携带重试间隔供客户端退避
            result = await limiter.check(request)
            if not result.allowed:
                raise HTTPException(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    detail=result.reason,
                    headers={"Retry-After": str(max(int(result.retry_after), 1))},
                )

            return await func(*args, **kwargs)

        return wrapper

    return decorator


async def rate_limit_dependency(
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> None:
    """FastAPI 依赖版限流入口。

    这里会先尝试解析用户身份，再统一执行限流。
    未登录请求自动回退到 IP 限流，已登录请求则可以触发用户维度限流。
    """

    try:
        # 先解析用户身份，使后续限流能按 user_id 维度生效
        await resolve_request_user_id(request=request, db=db)
        result = await unified_limiter.check(request)
        if not result.allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail=result.reason,
                headers={"Retry-After": str(max(int(result.retry_after), 1))},
            )
    except HTTPException:
        raise
    except Exception as exc:
        # 限流自身异常时降级放行，避免影响正常请求
        logger.warning("限流依赖执行异常，降级放行", error=str(exc), exc_info=True)


async def custom_rate_limit_handler(request: Request, exc: Exception) -> JSONResponse:
    """统一限流异常响应。"""

    return JSONResponse(
        status_code=429,
        content={
            "code": 429,
            "message": "请求过于频繁，请稍后再试",
            "detail": str(exc) if str(exc) else "Rate limit exceeded",
        },
    )
