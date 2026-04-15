# -*- coding: utf-8 -*-
"""统一限流调度器。"""

from __future__ import annotations  # 开启延迟解析类型注解，避免前向引用在导入阶段就被过早求值

from fastapi.requests import Request  # 从 fastapi.requests 模块导入当前文件后续要用到的对象

from configs.settings import get_settings  # 从 configs.settings 模块导入当前文件后续要用到的对象
from middlewares.rate_limit.config import (  # 从 middlewares.rate_limit.config 模块导入当前文件后续要用到的对象
    RateLimitConfig,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    RateLimitDimension,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    RateLimitIdentity,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    RateLimitResult,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
)  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
from middlewares.rate_limit.redis_limit import RedisRateLimit  # 从 middlewares.rate_limit.redis_limit 模块导入当前文件后续要用到的对象
from middlewares.rate_limit.token_bucket import LocalTokenBucket  # 从 middlewares.rate_limit.token_bucket 模块导入当前文件后续要用到的对象
from utils.logger import get_logger  # 从 utils.logger 模块导入当前文件后续要用到的对象

settings = get_settings()  # 把右边计算出来的结果保存到 settings 变量中，方便后面的代码继续复用
logger = get_logger(name="RateLimiter")  # 把右边计算出来的结果保存到 logger 变量中，方便后面的代码继续复用


class UnifiedRateLimiter:  # 定义 UnifiedRateLimiter 类，用来把这一块相关的状态和行为组织在一起
    """统一限流入口。"""

    def __init__(self, config: RateLimitConfig | None = None) -> None:  # 定义函数 __init__，把一段可以复用的逻辑单独封装起来
        """初始化统一限流器，并确定当前要使用的限流配置。"""
        self.cfg = config or RateLimitConfig()  # 把右边计算出来的结果保存到 cfg 变量中，方便后面的代码继续复用

    def _get_client_ip(self, request: Request) -> str:  # 定义函数 _get_client_ip，把一段可以复用的逻辑单独封装起来
        """提取客户端 IP。

        先读反向代理常见头，再回退到 `request.client.host`。
        """

        forwarded_for = request.headers.get("X-Forwarded-For")  # 把右边计算出来的结果保存到 forwarded_for 变量中，方便后面的代码继续复用
        if forwarded_for:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            return forwarded_for.split(",")[0].strip()  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

        real_ip = request.headers.get("X-Real-IP")  # 把右边计算出来的结果保存到 real_ip 变量中，方便后面的代码继续复用
        if real_ip:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            return real_ip.strip()  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

        return request.client.host if request.client else "unknown"  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    def _build_identity(self, request: Request) -> RateLimitIdentity:  # 定义函数 _build_identity，把一段可以复用的逻辑单独封装起来
        """根据请求和配置构造限流身份。"""

        ip = self._get_client_ip(request)  # 把右边计算出来的结果保存到 ip 变量中，方便后面的代码继续复用
        user_id = getattr(request.state, "user_id", None)  # 把右边计算出来的结果保存到 user_id 变量中，方便后面的代码继续复用

        if self.cfg.dimension == RateLimitDimension.IP:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            return RateLimitIdentity(key=f"ip:{ip}", ip=ip, user_id=None, scope="ip")  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

        if self.cfg.dimension == RateLimitDimension.USER_ID:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            if user_id is not None:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                return RateLimitIdentity(  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
                    key=f"user:{user_id}",  # 把右边计算出来的结果保存到 key 变量中，方便后面的代码继续复用
                    ip=ip,  # 把右边计算出来的结果保存到 ip 变量中，方便后面的代码继续复用
                    user_id=user_id,  # 把右边计算出来的结果保存到 user_id 变量中，方便后面的代码继续复用
                    scope="user",  # 把右边计算出来的结果保存到 scope 变量中，方便后面的代码继续复用
                )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
            return RateLimitIdentity(key=f"ip:{ip}", ip=ip, user_id=None, scope="ip")  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

        if user_id is not None:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            return RateLimitIdentity(  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
                key=f"user:{user_id}:ip:{ip}",  # 把右边计算出来的结果保存到 key 变量中，方便后面的代码继续复用
                ip=ip,  # 把右边计算出来的结果保存到 ip 变量中，方便后面的代码继续复用
                user_id=user_id,  # 把右边计算出来的结果保存到 user_id 变量中，方便后面的代码继续复用
                scope="combined",  # 把右边计算出来的结果保存到 scope 变量中，方便后面的代码继续复用
            )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级

        return RateLimitIdentity(key=f"ip:{ip}", ip=ip, user_id=None, scope="ip")  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    async def check(self, request: Request) -> RateLimitResult:  # 定义异步函数 check，调用它时通常需要配合 await 使用
        """执行完整限流流程。

        为了避免同一请求链路里被 dependency/middleware 重复执行，
        这里加入了请求级幂等保护。
        """

        if getattr(request.state, "_rate_limit_checked", False):  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            return getattr(  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
                request.state,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                "_rate_limit_result",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                RateLimitResult(allowed=True),  # 把右边计算出来的结果保存到 RateLimitResult(allowed 变量中，方便后面的代码继续复用
            )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级

        identity = self._build_identity(request)  # 把右边计算出来的结果保存到 identity 变量中，方便后面的代码继续复用

        try:  # 开始尝试执行可能出错的逻辑，如果报错就会转到下面的异常分支
            if await RedisRateLimit.is_in_blacklist(identity.key):  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                result = RateLimitResult(  # 把右边计算出来的结果保存到 result 变量中，方便后面的代码继续复用
                    allowed=False,  # 把右边计算出来的结果保存到 allowed 变量中，方便后面的代码继续复用
                    retry_after=float(settings.BLACKLIST_DURATION),  # 把右边计算出来的结果保存到 retry_after 变量中，方便后面的代码继续复用
                    reason="已被临时封禁，请稍后再试",  # 把右边计算出来的结果保存到 reason 变量中，方便后面的代码继续复用
                )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
                request.state._rate_limit_checked = True  # 把右边计算出来的结果保存到 request.state._rate_limit_checked 变量中，方便后面的代码继续复用
                request.state._rate_limit_result = result  # 把右边计算出来的结果保存到 request.state._rate_limit_result 变量中，方便后面的代码继续复用
                return result  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

            exceeded, count = await RedisRateLimit.anti_spam_check(identity)  # 把右边计算出来的结果保存到 exceeded, count 变量中，方便后面的代码继续复用
            if exceeded:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                await RedisRateLimit.add_to_blacklist(identity.key)  # 等待这个异步操作完成，再继续执行后面的代码
                result = RateLimitResult(  # 把右边计算出来的结果保存到 result 变量中，方便后面的代码继续复用
                    allowed=False,  # 把右边计算出来的结果保存到 allowed 变量中，方便后面的代码继续复用
                    retry_after=float(settings.BLACKLIST_DURATION),  # 把右边计算出来的结果保存到 retry_after 变量中，方便后面的代码继续复用
                    reason=f"请求频率过高（{count} 次），已自动封禁",  # 把右边计算出来的结果保存到 reason 变量中，方便后面的代码继续复用
                )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
                request.state._rate_limit_checked = True  # 把右边计算出来的结果保存到 request.state._rate_limit_checked 变量中，方便后面的代码继续复用
                request.state._rate_limit_result = result  # 把右边计算出来的结果保存到 request.state._rate_limit_result 变量中，方便后面的代码继续复用
                return result  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

            result = await RedisRateLimit.token_limit(identity, self.cfg)  # 把右边计算出来的结果保存到 result 变量中，方便后面的代码继续复用
            if "Redis异常" in result.reason and settings.ENABLE_LOCAL_FALLBACK:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                logger.warning("Redis 限流不可用，启用本地令牌桶降级", identity=identity.key)  # 记录一条日志，方便后续排查程序运行过程和定位问题
                bucket = await LocalTokenBucket.get_instance(  # 把右边计算出来的结果保存到 bucket 变量中，方便后面的代码继续复用
                    identity.key,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                    self.cfg.capacity,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                    self.cfg.rate,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
                result = await bucket.try_consume()  # 把右边计算出来的结果保存到 result 变量中，方便后面的代码继续复用

            request.state._rate_limit_checked = True  # 把右边计算出来的结果保存到 request.state._rate_limit_checked 变量中，方便后面的代码继续复用
            request.state._rate_limit_result = result  # 把右边计算出来的结果保存到 request.state._rate_limit_result 变量中，方便后面的代码继续复用
            return result  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
        except Exception as exc:  # 如果上面 try 里的代码报错，就进入这个异常处理分支
            logger.warning("统一限流执行异常，降级放行", error=str(exc), exc_info=True)  # 记录一条日志，方便后续排查程序运行过程和定位问题
            result = RateLimitResult(allowed=True, reason="限流服务异常，临时放行")  # 把右边计算出来的结果保存到 result 变量中，方便后面的代码继续复用
            request.state._rate_limit_checked = True  # 把右边计算出来的结果保存到 request.state._rate_limit_checked 变量中，方便后面的代码继续复用
            request.state._rate_limit_result = result  # 把右边计算出来的结果保存到 request.state._rate_limit_result 变量中，方便后面的代码继续复用
            return result  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束


unified_limiter = UnifiedRateLimiter()  # 把右边计算出来的结果保存到 unified_limiter 变量中，方便后面的代码继续复用
