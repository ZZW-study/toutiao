"""
SingleFlight 异步并发合并工具
核心作用：合并相同key的并发请求，仅执行一次耗时操作（DB/远程调用）
解决问题：缓存击穿、重复请求导致的服务压力
大厂标准：异步安全、无锁设计、异常隔离
"""
import asyncio
from typing import Any, Callable, Optional, Dict
from utils.logger import logger

# 全局常量
DEFAULT_SINGLE_FLIGHT_TIMEOUT = 5  # 单请求超时时间(秒)


class SingleFlight:
    """异步 SingleFlight 实现（协程安全）"""
    _instance: Optional["SingleFlight"] = None
    _lock = asyncio.Lock()

    def __new__(cls, *args, **kwargs):
        """单例模式"""
        if cls._instance is None:
                cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        # 存储正在执行的任务：key -> future
        """初始化正在飞行中的请求映射表，用于合并并发请求。"""
        self._inflight: Dict[str, asyncio.Future] = {}  # 结果占位符，专门表示还未执行完成的异步操作的最终结果。

    async def do(self, key: str, func: Callable[[], Any]) -> Any:
        """执行并发合并。

        asyncio.Future 原理：
        - Future 是一个"结果占位符"，初始状态为 PENDING
        - await future 会挂起协程，把自己加入 Future 内部的 _waiters 列表
        - set_result() 会遍历 _waiters，把所有等待者放入事件循环就绪队列
        - 下一轮事件循环，所有等待者被调度执行，收到结果

        执行流程：
        请求A: 创建Future → 查数据库... → set_result(张三) → 返回
        请求B:                    ↓ await Future ↓              → 收到张三
        请求C:                    ↓ await Future ↓              → 收到张三
                                    ↑
                          所有请求等待同一个 Future
                          set_result 后全部唤醒
        """
        # 1. 检查是否已有相同任务在执行
        if key in self._inflight:
            logger.debug(f"[SingleFlight] 合并重复请求 | key={key}")
            return await self._inflight[key]  # 等待同一个 Future，set_result 后自动收到结果

        # 2. 创建 Future，存储并发任务
        future = asyncio.Future()  # 结果占位符，初始状态未完成
        self._inflight[key] = future

        try:
            # 3. 执行目标函数（带超时保护）
            result = await asyncio.wait_for(func(), timeout=DEFAULT_SINGLE_FLIGHT_TIMEOUT)
            future.set_result(result)  # 设置结果，所有等待这个 Future 的协程都会收到 result
            return result
        except Exception as e:
            # 异常隔离：不影响其他请求
            future.set_exception(e)  # 设置异常，所有等待的协程都会收到异常
            logger.error(f"[SingleFlight] 执行失败 | key={key}, err={str(e)}")
            raise
        finally:
            # 4. 执行完成，清理任务
            self._inflight.pop(key, None)

    async def clear(self):
        """清理所有任务（运维/重启专用）"""
        self._inflight.clear()
        logger.warning("[SingleFlight] 已清空所有任务")


# 全局单例实例
singleflight = SingleFlight()
