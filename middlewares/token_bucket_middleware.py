# -*- coding: utf-8 -*-
"""令牌桶限流中间件。

基于 Redis + Lua 脚本实现的令牌桶算法，对每个客户端 IP 进行请求限流。
使用 FastAPI/Starlette 的 BaseHTTPMiddleware 基类，以便在每个请求进入路由前进行拦截。
"""
# Request 是一个类，它封装了 HTTP 请求的所有数据：
# 请求方法（GET、POST 等）
# URL 路径和查询参数（?name=张三）
# 请求头（Headers，如 User-Agent、Authorization）
# 请求体（Body，如 JSON 数据）
# 客户端 IP、Cookie 等
# 你可以在自己的路由函数或中间件中声明一个参数类型为 Request，FastAPI 就会自动把当前请求的对象传进来。
from fastapi import Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from configs.redis import redis_client
from configs.settings import get_settings
from middlewares.rate_limit import token_limit
from utils.logger import get_logger

logger = get_logger(name="TokenBucketMiddleware")
settings = get_settings()


class TokenBucketRateLimitMiddleware(BaseHTTPMiddleware):
    """Redis令牌桶限流中间件。

    继承自 BaseHTTPMiddleware，重写 dispatch 方法。
    然后基于客户端 IP 调用 token_limit 进行限流决策。
    如果被限流，返回 HTTP 429 并附带重试等待时间；否则放行。
    """

    async def dispatch(self, request: Request, call_next):
        """处理请求的核心方法。"""

        # ---------- 1. 限流主逻辑，捕获异常保证服务可用 ----------
        try:
            # 获取客户端真实 IP
            # request.client 可能为 None（例如测试环境），此时用 "unknown" 代替
            client_ip = request.client.host if request.client else "unknown"

            # 构造 Redis 键名，格式固定便于区分
            redis_key = f"rl:{client_ip}"

            # 调用令牌桶限流核心函数，返回限流结果
            result = await token_limit(
                redis_client,
                redis_key,
                capacity=settings.TOKEN_BUCKET_CAPACITY,
                rate=settings.TOKEN_BUCKET_RATE,
            )

            # 如果不允许通过（桶内令牌不足）
            if not result.allowed:
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "code": 429,
                        "message": "请求过于频繁，请稍后再试",
                        "data": {"retry_after": round(result.retry_after, 2)}
                    },
                    # 标准 HTTP 头部，告知客户端需要等待的秒数（取整 + 1 避免重试过早）
                    headers={"Retry-After": str(int(result.retry_after) + 1)},
                )

            # 允许通过，继续处理后续中间件或路由
            return await call_next(request)

        except Exception as exc:
            logger.error("[限流中间件] 异常: %s", str(exc), exc_info=True)
            # 放行请求，保证服务高可用（降级策略）
            return await call_next(request)