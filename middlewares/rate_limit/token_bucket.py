# -*- coding: utf-8 -*-
"""本地令牌桶实现。

高性能本地限流，使用内存存储令牌状态。
支持 LRU 策略清理旧实例，防止内存泄漏。
"""


import time  # 导入 time 模块，给当前文件后面的逻辑使用
import asyncio  # 导入 asyncio 模块，给当前文件后面的逻辑使用
from typing import Dict  # 从 typing 模块导入当前文件后续要用到的对象

from utils.logger import get_logger  # 从 utils.logger 模块导入当前文件后续要用到的对象
from middlewares.rate_limit.config import RateLimitConfig, RateLimitResult  # 从 middlewares.rate_limit.config 模块导入当前文件后续要用到的对象


logger = get_logger(name="LocalTokenBucket")  # 把右边计算出来的结果保存到 logger 变量中，方便后面的代码继续复用


class LocalTokenBucket:  # 定义 LocalTokenBucket 类，用来把这一块相关的状态和行为组织在一起
    """
    本地令牌桶实现

    特性：
    - 异步安全：每个桶有独立的锁
    - LRU 清理：实例数超阈值自动清理旧实例
    - 自动补充：根据时间差自动计算令牌补充
    """
    _instances: Dict[str, "LocalTokenBucket"] = {}  # 把右边计算出来的结果保存到 _instances 变量中，方便后面的代码继续复用
    _lock: asyncio.Lock = asyncio.Lock()  # 把右边计算出来的结果保存到 _lock 变量中，方便后面的代码继续复用
    _max_instances: int = 10000  # 最大实例数，防止内存泄漏

    def __init__(self, capacity: int = None, rate: float = None):  # 定义函数 __init__，把一段可以复用的逻辑单独封装起来
        """初始化本地令牌桶的容量、速率和并发保护锁。"""
        self.capacity = capacity or RateLimitConfig.capacity  # 把右边计算出来的结果保存到 capacity 变量中，方便后面的代码继续复用
        self.rate = rate or RateLimitConfig.rate  # 把右边计算出来的结果保存到 rate 变量中，方便后面的代码继续复用
        self.tokens = float(self.capacity)  # 把右边计算出来的结果保存到 tokens 变量中，方便后面的代码继续复用
        self.last_refill_time = time.time()  # 把右边计算出来的结果保存到 last_refill_time 变量中，方便后面的代码继续复用
        self._refill_lock = asyncio.Lock()  # 每个桶自己的锁，防止竞态条件

    @classmethod  # 使用 classmethod 装饰下面的函数或类，给它附加额外能力
    async def get_instance(cls, key: str, capacity: int = None, rate: float = None) -> "LocalTokenBucket":  # 定义异步函数 get_instance，调用它时通常需要配合 await 使用
        """
        获取或创建令牌桶实例（线程安全）
        使用LRU策略：当实例数超过阈值时，清理最旧的实例
        """
        async with cls._lock:  # 以异步上下文管理的方式使用资源，结束时会自动做清理
            if key not in cls._instances:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                # 检查是否需要清理（防止内存泄漏）
                if len(cls._instances) >= cls._max_instances:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                    # 清理一半的最旧实例
                    keys_to_remove = list(cls._instances.keys())[:cls._max_instances // 2]  # 把右边计算出来的结果保存到 keys_to_remove 变量中，方便后面的代码继续复用
                    for k in keys_to_remove:  # 开始遍历可迭代对象里的每一项，并对每一项执行同样的处理
                        del cls._instances[k]  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                    logger.warning(f"[本地令牌桶] 已清理 {len(keys_to_remove)} 个旧实例")  # 记录一条日志，方便后续排查程序运行过程和定位问题

                cls._instances[key] = cls(capacity, rate)  # 把右边计算出来的结果保存到 _instances[key] 变量中，方便后面的代码继续复用
            return cls._instances[key]  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    async def _refill(self) -> None:  # 定义异步函数 _refill，调用它时通常需要配合 await 使用
        """补充令牌（异步安全）"""
        async with self._refill_lock:  # 以异步上下文管理的方式使用资源，结束时会自动做清理
            now = time.time()  # 把右边计算出来的结果保存到 now 变量中，方便后面的代码继续复用
            elapsed_time = now - self.last_refill_time  # 把右边计算出来的结果保存到 elapsed_time 变量中，方便后面的代码继续复用
            new_tokens = elapsed_time * self.rate  # 把右边计算出来的结果保存到 new_tokens 变量中，方便后面的代码继续复用
            self.tokens = min(self.tokens + new_tokens, self.capacity)  # 把右边计算出来的结果保存到 tokens 变量中，方便后面的代码继续复用
            self.last_refill_time = now  # 把右边计算出来的结果保存到 last_refill_time 变量中，方便后面的代码继续复用

    async def try_consume(self, tokens: float = 1.0) -> RateLimitResult:  # 定义异步函数 try_consume，调用它时通常需要配合 await 使用
        """尝试消费令牌（异步安全）"""
        await self._refill()  # 等待这个异步操作完成，再继续执行后面的代码
        if self.tokens >= tokens:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            self.tokens -= tokens  # 把右边计算出来的结果保存到 tokens - 变量中，方便后面的代码继续复用
            return RateLimitResult(allowed=True, remaining_tokens=self.tokens)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
        need_tokens = tokens - self.tokens  # 把右边计算出来的结果保存到 need_tokens 变量中，方便后面的代码继续复用
        wait_time = need_tokens / self.rate  # 把右边计算出来的结果保存到 wait_time 变量中，方便后面的代码继续复用
        return RateLimitResult(  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
            allowed=False,  # 把右边计算出来的结果保存到 allowed 变量中，方便后面的代码继续复用
            retry_after=wait_time,  # 把右边计算出来的结果保存到 retry_after 变量中，方便后面的代码继续复用
            remaining_tokens=self.tokens,  # 把右边计算出来的结果保存到 remaining_tokens 变量中，方便后面的代码继续复用
            reason="本地令牌不足，请求频繁"  # 把右边计算出来的结果保存到 reason 变量中，方便后面的代码继续复用
        )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
