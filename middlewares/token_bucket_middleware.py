"""
令牌桶限流中间件。

这里把统一限流器接入 FastAPI 请求链路，对全部业务请求做入口保护。
"""

import time

from fastapi import HTTPException, Request, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from middlewares.token_bucket_rate_limit import unified_limiter
from utils.logger import get_logger

logger = get_logger(name="TokenBucketMiddleware")


class TokenBucketRateLimitMiddleware(BaseHTTPMiddleware):
    """
    统一限流中间件。

    设计思路：
    1. 中间件只负责拦截和返回标准响应，不关心具体限流实现细节。
    2. 真正的限流判断交给 `unified_limiter`，这样装饰器和中间件可以共用同一套规则。
    3. 当限流组件自身异常时选择放行，避免因为基础设施抖动把整个服务拖垮。
    """

    async def dispatch(self, request: Request, call_next):
        """拦截 HTTP 请求，统一执行限流并决定是否继续放行。"""
        start_time = time.time()

        # 这些路径通常用于健康检查、接口文档和网关探活。
        # 如果这里也套严格限流，很容易导致监控误报或者本地调试异常。
        skip_paths = {"/", "/health", "/docs", "/openapi.json", "/redoc"}
        if request.url.path in skip_paths:
            return await call_next(request)

        try:
            # 统一限流器会根据当前配置优先走 Redis 分布式限流，
            # 必要时再回退到本地桶。中间件只消费判断结果，职责保持单一。
            result = await unified_limiter.check(request)

            if not result.allowed:
                client_ip = request.client.host if request.client else "unknown"

                # 详细记录被拦截请求，方便后续定位是攻击流量还是阈值设置不合理。
                logger.warning(
                    "[限流] 请求被拦截 | IP: %s | Path: %s | Method: %s | Reason: %s | Retry-After: %.2fs",
                    client_ip,
                    request.url.path,
                    request.method,
                    result.reason,
                    result.retry_after,
                )

                # 将重试时间和剩余令牌暴露给客户端，前端/网关可以据此做退避控制。
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "code": 429,
                        "message": result.reason or "请求过于频繁，请稍后再试",
                        "data": {
                            "retry_after": round(result.retry_after, 2),
                        },
                    },
                    headers={
                        "Retry-After": str(int(result.retry_after) + 1),
                        "X-RateLimit-Remaining": str(result.remaining_tokens),
                    },
                )

            response = await call_next(request)

            # 记录限流检查的额外耗时，帮助判断限流链路是否成为性能瓶颈。
            process_time = (time.time() - start_time) * 1000
            logger.debug(
                "[限流] 请求通过 | IP: %s | Path: %s | Duration: %.2fms",
                request.client.host if request.client else "unknown",
                request.url.path,
                process_time,
            )
            return response

        except HTTPException:
            # 保留业务层抛出的 HTTP 语义，不能在中间件里吞掉。
            raise
        except Exception as exc:
            # 限流系统异常时主动降级放行，优先保证服务可用性。
            logger.error("[限流中间件] 异常: %s", str(exc), exc_info=True)
            return await call_next(request)
