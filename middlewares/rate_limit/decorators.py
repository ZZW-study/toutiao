# -*- coding: utf-8 -*-
"""限流装饰器与 FastAPI 依赖。"""

from __future__ import annotations  # 开启延迟解析类型注解，避免前向引用在导入阶段就被过早求值

from functools import wraps  # 从 functools 模块导入当前文件后续要用到的对象
from typing import Any, Callable, Coroutine, TypeVar  # 从 typing 模块导入当前文件后续要用到的对象

from fastapi import Depends, HTTPException, status  # 从 fastapi 模块导入当前文件后续要用到的对象
from fastapi.requests import Request  # 从 fastapi.requests 模块导入当前文件后续要用到的对象
from fastapi.responses import JSONResponse  # 从 fastapi.responses 模块导入当前文件后续要用到的对象
from sqlalchemy.ext.asyncio import AsyncSession  # 从 sqlalchemy.ext.asyncio 模块导入当前文件后续要用到的对象

from configs.db import get_db  # 从 configs.db 模块导入当前文件后续要用到的对象
from middlewares.rate_limit.config import RateLimitConfig, RateLimitDimension  # 从 middlewares.rate_limit.config 模块导入当前文件后续要用到的对象
from middlewares.rate_limit.limiter import UnifiedRateLimiter, unified_limiter  # 从 middlewares.rate_limit.limiter 模块导入当前文件后续要用到的对象
from utils.auth import resolve_request_user_id  # 从 utils.auth 模块导入当前文件后续要用到的对象
from utils.logger import get_logger  # 从 utils.logger 模块导入当前文件后续要用到的对象

T = TypeVar("T")  # 把这个常量值保存到 T 中，后面会作为固定配置反复使用
logger = get_logger(name="RateLimit")  # 把右边计算出来的结果保存到 logger 变量中，方便后面的代码继续复用


def _find_request(args: tuple[Any, ...], kwargs: dict[str, Any]) -> Request | None:  # 定义函数 _find_request，把一段可以复用的逻辑单独封装起来
    """从位置参数或关键字参数中提取 Request。"""

    request = kwargs.get("request")  # 把右边计算出来的结果保存到 request 变量中，方便后面的代码继续复用
    if isinstance(request, Request):  # 开始判断当前条件是否成立，再决定后面该走哪个分支
        return request  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    for arg in args:  # 开始遍历可迭代对象里的每一项，并对每一项执行同样的处理
        if isinstance(arg, Request):  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            return arg  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    return None  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束


def _build_config(  # 定义函数 _build_config，把一段可以复用的逻辑单独封装起来
    capacity: int | None,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    rate: float | None,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    dimension: RateLimitDimension | None,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
) -> RateLimitConfig:  # 这一行开始一个新的代码块，下面缩进的内容都属于它
    """把装饰器参数覆盖到默认配置上。"""

    base = RateLimitConfig()  # 把右边计算出来的结果保存到 base 变量中，方便后面的代码继续复用
    return RateLimitConfig(  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
        capacity=capacity if capacity is not None else base.capacity,  # 把右边计算出来的结果保存到 capacity 变量中，方便后面的代码继续复用
        rate=rate if rate is not None else base.rate,  # 把右边计算出来的结果保存到 rate 变量中，方便后面的代码继续复用
        dimension=dimension if dimension is not None else base.dimension,  # 把右边计算出来的结果保存到 dimension 变量中，方便后面的代码继续复用
    )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级


def rate_limit(  # 定义函数 rate_limit，把一段可以复用的逻辑单独封装起来
    capacity: int | None = None,  # 把右边计算出来的结果保存到 capacity 变量中，方便后面的代码继续复用
    rate: float | None = None,  # 把右边计算出来的结果保存到 rate 变量中，方便后面的代码继续复用
    dimension: RateLimitDimension | None = None,  # 把右边计算出来的结果保存到 dimension 变量中，方便后面的代码继续复用
) -> Callable[[Callable[..., Coroutine[Any, Any, T]]], Callable[..., Coroutine[Any, Any, T]]]:  # 这一行开始一个新的代码块，下面缩进的内容都属于它
    """为单个接口附加自定义限流规则。"""

    config = _build_config(capacity=capacity, rate=rate, dimension=dimension)  # 把右边计算出来的结果保存到 config 变量中，方便后面的代码继续复用
    limiter = UnifiedRateLimiter(config)  # 把右边计算出来的结果保存到 limiter 变量中，方便后面的代码继续复用

    def decorator(  # 定义函数 decorator，把一段可以复用的逻辑单独封装起来
        func: Callable[..., Coroutine[Any, Any, T]]  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    ) -> Callable[..., Coroutine[Any, Any, T]]:  # 这一行开始一个新的代码块，下面缩进的内容都属于它
        """接收原函数并返回带限流校验的包装函数。"""

        @wraps(func)  # 使用 wraps 装饰下面的函数或类，给它附加额外能力
        async def wrapper(*args: Any, **kwargs: Any) -> T:  # 定义异步函数 wrapper，调用它时通常需要配合 await 使用
            """在执行真实路由前，先完成请求级限流检查。"""
            request = _find_request(args, kwargs)  # 把右边计算出来的结果保存到 request 变量中，方便后面的代码继续复用
            if request is None:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                # 没有 Request 说明当前函数并不是 FastAPI 路由，直接放行。
                return await func(*args, **kwargs)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

            result = await limiter.check(request)  # 把右边计算出来的结果保存到 result 变量中，方便后面的代码继续复用
            if not result.allowed:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                raise HTTPException(  # 主动抛出异常，让上层知道这里出现了需要处理的问题
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,  # 把右边计算出来的结果保存到 status_code 变量中，方便后面的代码继续复用
                    detail=result.reason,  # 把右边计算出来的结果保存到 detail 变量中，方便后面的代码继续复用
                    headers={"Retry-After": str(max(int(result.retry_after), 1))},  # 把右边计算出来的结果保存到 headers 变量中，方便后面的代码继续复用
                )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级

            return await func(*args, **kwargs)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

        return wrapper  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    return decorator  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束


async def rate_limit_dependency(  # 定义异步函数 rate_limit_dependency，调用它时通常需要配合 await 使用
    request: Request,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    db: AsyncSession = Depends(get_db),  # 把右边计算出来的结果保存到 db 变量中，方便后面的代码继续复用
) -> None:  # 这一行开始一个新的代码块，下面缩进的内容都属于它
    """FastAPI 依赖版限流入口。

    这里会先尝试解析用户身份，再统一执行限流。
    未登录请求自动回退到 IP 限流，已登录请求则可以触发用户维度限流。
    """

    try:  # 开始尝试执行可能出错的逻辑，如果报错就会转到下面的异常分支
        await resolve_request_user_id(request=request, db=db)  # 等待这个异步操作完成，再继续执行后面的代码
        result = await unified_limiter.check(request)  # 把右边计算出来的结果保存到 result 变量中，方便后面的代码继续复用
        if not result.allowed:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            raise HTTPException(  # 主动抛出异常，让上层知道这里出现了需要处理的问题
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,  # 把右边计算出来的结果保存到 status_code 变量中，方便后面的代码继续复用
                detail=result.reason,  # 把右边计算出来的结果保存到 detail 变量中，方便后面的代码继续复用
                headers={"Retry-After": str(max(int(result.retry_after), 1))},  # 把右边计算出来的结果保存到 headers 变量中，方便后面的代码继续复用
            )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
    except HTTPException:  # 如果上面 try 里的代码报错，就进入这个异常处理分支
        raise  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    except Exception as exc:  # 如果上面 try 里的代码报错，就进入这个异常处理分支
        logger.warning("限流依赖执行异常，降级放行", error=str(exc), exc_info=True)  # 记录一条日志，方便后续排查程序运行过程和定位问题


async def custom_rate_limit_handler(request: Request, exc: Exception) -> JSONResponse:  # 定义异步函数 custom_rate_limit_handler，调用它时通常需要配合 await 使用
    """统一限流异常响应。"""

    return JSONResponse(  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
        status_code=429,  # 把右边计算出来的结果保存到 status_code 变量中，方便后面的代码继续复用
        content={  # 把右边计算出来的结果保存到 content 变量中，方便后面的代码继续复用
            "code": 429,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
            "message": "请求过于频繁，请稍后再试",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
            "detail": str(exc) if str(exc) else "Rate limit exceeded",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        },  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
    )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
