"""
令牌桶限流中间件。

这里把统一限流器接入 FastAPI 请求链路，对全部业务请求做入口保护。
"""

import time  # 导入 time 模块，给当前文件后面的逻辑使用

from fastapi import HTTPException, Request, status  # 从 fastapi 模块导入当前文件后续要用到的对象
from starlette.middleware.base import BaseHTTPMiddleware  # 从 starlette.middleware.base 模块导入当前文件后续要用到的对象
from starlette.responses import JSONResponse  # 从 starlette.responses 模块导入当前文件后续要用到的对象

from middlewares.token_bucket_rate_limit import unified_limiter  # 从 middlewares.token_bucket_rate_limit 模块导入当前文件后续要用到的对象
from utils.logger import get_logger  # 从 utils.logger 模块导入当前文件后续要用到的对象

logger = get_logger(name="TokenBucketMiddleware")  # 把右边计算出来的结果保存到 logger 变量中，方便后面的代码继续复用


class TokenBucketRateLimitMiddleware(BaseHTTPMiddleware):  # 定义 TokenBucketRateLimitMiddleware 类，用来把这一块相关的状态和行为组织在一起
    """
    统一限流中间件。

    设计思路：
    1. 中间件只负责拦截和返回标准响应，不关心具体限流实现细节。
    2. 真正的限流判断交给 `unified_limiter`，这样装饰器和中间件可以共用同一套规则。
    3. 当限流组件自身异常时选择放行，避免因为基础设施抖动把整个服务拖垮。
    """

    async def dispatch(self, request: Request, call_next):  # 定义异步函数 dispatch，调用它时通常需要配合 await 使用
        """拦截 HTTP 请求，统一执行限流并决定是否继续放行。"""
        start_time = time.time()  # 把右边计算出来的结果保存到 start_time 变量中，方便后面的代码继续复用

        # 这些路径通常用于健康检查、接口文档和网关探活。
        # 如果这里也套严格限流，很容易导致监控误报或者本地调试异常。
        skip_paths = {"/", "/health", "/docs", "/openapi.json", "/redoc"}  # 把右边计算出来的结果保存到 skip_paths 变量中，方便后面的代码继续复用
        if request.url.path in skip_paths:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            return await call_next(request)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

        try:  # 开始尝试执行可能出错的逻辑，如果报错就会转到下面的异常分支
            # 统一限流器会根据当前配置优先走 Redis 分布式限流，
            # 必要时再回退到本地桶。中间件只消费判断结果，职责保持单一。
            result = await unified_limiter.check(request)  # 把右边计算出来的结果保存到 result 变量中，方便后面的代码继续复用

            if not result.allowed:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                client_ip = request.client.host if request.client else "unknown"  # 把右边计算出来的结果保存到 client_ip 变量中，方便后面的代码继续复用

                # 详细记录被拦截请求，方便后续定位是攻击流量还是阈值设置不合理。
                logger.warning(  # 记录一条日志，方便后续排查程序运行过程和定位问题
                    "[限流] 请求被拦截 | IP: %s | Path: %s | Method: %s | Reason: %s | Retry-After: %.2fs",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                    client_ip,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                    request.url.path,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                    request.method,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                    result.reason,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                    result.retry_after,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级

                # 将重试时间和剩余令牌暴露给客户端，前端/网关可以据此做退避控制。
                return JSONResponse(  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
                    status_code=status.HTTP_429_TOO_MANY_REQUESTS,  # 把右边计算出来的结果保存到 status_code 变量中，方便后面的代码继续复用
                    content={  # 把右边计算出来的结果保存到 content 变量中，方便后面的代码继续复用
                        "code": 429,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                        "message": result.reason or "请求过于频繁，请稍后再试",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                        "data": {  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                            "retry_after": round(result.retry_after, 2),  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                        },  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
                    },  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
                    headers={  # 把右边计算出来的结果保存到 headers 变量中，方便后面的代码继续复用
                        "Retry-After": str(int(result.retry_after) + 1),  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                        "X-RateLimit-Remaining": str(result.remaining_tokens),  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                    },  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
                )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级

            response = await call_next(request)  # 把右边计算出来的结果保存到 response 变量中，方便后面的代码继续复用

            # 记录限流检查的额外耗时，帮助判断限流链路是否成为性能瓶颈。
            process_time = (time.time() - start_time) * 1000  # 把右边计算出来的结果保存到 process_time 变量中，方便后面的代码继续复用
            logger.debug(  # 记录一条日志，方便后续排查程序运行过程和定位问题
                "[限流] 请求通过 | IP: %s | Path: %s | Duration: %.2fms",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                request.client.host if request.client else "unknown",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                request.url.path,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                process_time,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
            )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
            return response  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

        except HTTPException:  # 如果上面 try 里的代码报错，就进入这个异常处理分支
            # 保留业务层抛出的 HTTP 语义，不能在中间件里吞掉。
            raise  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        except Exception as exc:  # 如果上面 try 里的代码报错，就进入这个异常处理分支
            # 限流系统异常时主动降级放行，优先保证服务可用性。
            logger.error("[限流中间件] 异常: %s", str(exc), exc_info=True)  # 记录一条日志，方便后续排查程序运行过程和定位问题
            return await call_next(request)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
