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
        """
        执行并发合并
        :param key: 唯一标识（相同key的请求会被合并）
        :param func: 实际要执行的异步函数
        :return: 执行结果
        """
        # 1. 检查是否已有相同任务在执行
        if key in self._inflight:
            logger.debug(f"[SingleFlight] 合并重复请求 | key={key}")
            return await self._inflight[key]

        # 2. 创建Future，存储并发任务
        future = asyncio.Future()
        self._inflight[key] = future

        try:
            # 3. 执行目标函数（带超时保护）
            result = await asyncio.wait_for(func(), timeout=DEFAULT_SINGLE_FLIGHT_TIMEOUT)
            future.set_result(result)
            return result
        except Exception as e:
            # 异常隔离：不影响其他请求
            future.set_exception(e)
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
