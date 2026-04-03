"""
令牌桶限流中间件
集成到FastAPI应用中，对所有请求进行限流检查
"""
from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
import time

from middlewares.token_bucket_rate_limit import unified_limiter, settings
from utils.logger import get_logger

logger = get_logger(name="TokenBucketMiddleware")


class TokenBucketRateLimitMiddleware(BaseHTTPMiddleware):
    """
    令牌桶限流中间件
    功能：
    1. 对所有请求进行限流检查
    2. 记录限流日志
    3. 限流时返回友好提示
    """
    
    async def dispatch(self, request: Request, call_next):
        start_time = time.time()
        
        # 跳过健康检查等特定路径
        skip_paths = ["/", "/health", "/docs", "/openapi.json", "/redoc"]
        if request.url.path in skip_paths:
            return await call_next(request)
        
        try:
            # 执行限流检查
            result = await unified_limiter.check(request)
            
            if not result.allowed:
                # 记录限流日志
                logger.warning(
                    f"[限流] 请求被拦截 | "
                    f"IP: {request.client.host if request.client else 'unknown'} | "
                    f"Path: {request.url.path} | "
                    f"Method: {request.method} | "
                    f"Reason: {result.reason} | "
                    f"Retry-After: {result.retry_after:.2f}s"
                )
                
                # 返回限流响应
                return JSONResponse(
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                    content={
                        "code": 429,
                        "message": result.reason or "请求过于频繁，请稍后再试",
                        "data": {
                            "retry_after": round(result.retry_after, 2)
                        }
                    },
                    headers={
                        "Retry-After": str(int(result.retry_after) + 1),
                        "X-RateLimit-Remaining": str(result.remaining_tokens)
                    }
                )
            
            # 限流通过，继续处理请求
            response = await call_next(request)
            
            # 记录成功请求的限流信息（可选）
            process_time = (time.time() - start_time) * 1000
            logger.debug(
                f"[限流] 请求通过 | "
                f"IP: {request.client.host if request.client else 'unknown'} | "
                f"Path: {request.url.path} | "
                f"Duration: {process_time:.2f}ms"
            )
            
            return response
            
        except HTTPException:
            # 重新抛出HTTP异常
            raise
        except Exception as e:
            # 限流服务异常时，放行请求（保证可用性）
            logger.error(f"[限流中间件] 异常: {str(e)}", exc_info=True)
            return await call_next(request)