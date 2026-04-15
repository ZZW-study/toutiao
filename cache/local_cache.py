"""本地缓存实现。

这一层只负责进程内短 TTL 热点缓存，不承担跨进程共享职责。
相比旧实现，这里重点修复了三个问题：

1. 读写都在同一把锁内完成，避免“检查存在后在锁外取值”的竞态。
2. 明确区分“未命中”和“命中了空值缓存”。
3. 不再额外起后台清理线程，而是在访问时顺手回收过期数据，降低复杂度。
"""

from __future__ import annotations  # 开启延迟解析类型注解，避免前向引用在导入阶段就被过早求值

import time  # 导入 time 模块，给当前文件后面的逻辑使用
from collections import OrderedDict  # 从 collections 模块导入当前文件后续要用到的对象
from dataclasses import dataclass  # 从 dataclasses 模块导入当前文件后续要用到的对象
from threading import RLock  # 从 threading 模块导入当前文件后续要用到的对象
from typing import Any, Dict, Optional  # 从 typing 模块导入当前文件后续要用到的对象

from cache.constants import EMPTY_CACHE_FLAG  # 从 cache.constants 模块导入当前文件后续要用到的对象
from utils.logger import get_logger  # 从 utils.logger 模块导入当前文件后续要用到的对象


@dataclass(slots=True)  # 使用 dataclass 装饰下面的函数或类，给它附加额外能力
class LocalCacheEntry:  # 定义 LocalCacheEntry 类，用来把这一块相关的状态和行为组织在一起
    """本地缓存命中结果。

    `hit=True` 表示当前 key 在缓存中存在，即使业务值为 `None` 也算命中。
    这样上层多级缓存就能区分“负缓存命中”和“完全未命中”。
    """

    hit: bool  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    value: Any = None  # 把右边计算出来的结果保存到 value 变量中，方便后面的代码继续复用


@dataclass(slots=True)  # 使用 dataclass 装饰下面的函数或类，给它附加额外能力
class _StoredValue:  # 定义 _StoredValue 类，用来把这一块相关的状态和行为组织在一起
    """本地缓存内部存储结构。"""

    value: Any  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    expire_at: float  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行


class LocalLRUCache:  # 定义 LocalLRUCache 类，用来把这一块相关的状态和行为组织在一起
    """线程安全的本地 LRU + TTL 缓存。

    设计取舍：
    - 使用 `OrderedDict` 明确维护 LRU 顺序，逻辑直观，便于加中文注释。
    - TTL 按条目单独记录，兼容不同 key 传入不同 TTL。
    - 只在访问路径上做轻量清理，避免后台线程带来的生命周期问题。
    """

    def __init__(self, maxsize: int = 1000, ttl: int = 300) -> None:  # 定义函数 __init__，把一段可以复用的逻辑单独封装起来
        """初始化本地缓存的容量、默认 TTL、锁和统计字段。"""
        self.maxsize = maxsize  # 把右边计算出来的结果保存到 maxsize 变量中，方便后面的代码继续复用
        self.ttl = ttl  # 把右边计算出来的结果保存到 ttl 变量中，方便后面的代码继续复用
        self._cache: "OrderedDict[Any, _StoredValue]" = OrderedDict()  # 把右边计算出来的结果保存到 _cache 变量中，方便后面的代码继续复用
        self._lock = RLock()  # 把右边计算出来的结果保存到 _lock 变量中，方便后面的代码继续复用
        self._empty_marker = EMPTY_CACHE_FLAG  # 把右边计算出来的结果保存到 _empty_marker 变量中，方便后面的代码继续复用

        # 下面这组统计字段保留给排查缓存命中率使用。
        self.hit_count = 0  # 把右边计算出来的结果保存到 hit_count 变量中，方便后面的代码继续复用
        self.miss_count = 0  # 把右边计算出来的结果保存到 miss_count 变量中，方便后面的代码继续复用
        self.total_count = 0  # 把右边计算出来的结果保存到 total_count 变量中，方便后面的代码继续复用

        self.logger = get_logger(name="LocalLRUCache")  # 把右边计算出来的结果保存到 logger 变量中，方便后面的代码继续复用

    def _now(self) -> float:  # 定义函数 _now，把一段可以复用的逻辑单独封装起来
        """返回单调时钟时间，避免系统时间回拨影响过期判断。"""
        return time.monotonic()  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    def _purge_expired_locked(self) -> None:  # 定义函数 _purge_expired_locked，把一段可以复用的逻辑单独封装起来
        """删除已过期的 key。

        这里必须在持锁状态下调用，否则会出现遍历和删除并发冲突。
        """

        now = self._now()  # 把右边计算出来的结果保存到 now 变量中，方便后面的代码继续复用
        expired_keys = [  # 把右边计算出来的结果保存到 expired_keys 变量中，方便后面的代码继续复用
            key for key, stored in self._cache.items() if stored.expire_at <= now  # 把右边计算出来的结果保存到 key for key, stored in _cache.items() if stored.expire_at < 变量中，方便后面的代码继续复用
        ]  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
        for key in expired_keys:  # 开始遍历可迭代对象里的每一项，并对每一项执行同样的处理
            self._cache.pop(key, None)  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行

    def _ensure_capacity_locked(self) -> None:  # 定义函数 _ensure_capacity_locked，把一段可以复用的逻辑单独封装起来
        """在写入后执行 LRU 淘汰。"""

        while len(self._cache) > self.maxsize:  # 只要条件一直成立，就会持续重复执行下面这个循环体
            # `last=False` 表示弹出最久未使用的条目。
            evicted_key, _ = self._cache.popitem(last=False)  # 把右边计算出来的结果保存到 evicted_key, _ 变量中，方便后面的代码继续复用
            self.logger.debug("本地缓存触发 LRU 淘汰", key=evicted_key)  # 记录一条调试日志，说明当前写入触发了 LRU 淘汰，方便后续排查缓存行为

    def get_entry(self, key: Any) -> LocalCacheEntry:  # 定义函数 get_entry，把一段可以复用的逻辑单独封装起来
        """返回带命中状态的读取结果。"""

        with self._lock:  # 以上下文管理的方式使用资源，离开代码块时会自动释放或关闭
            self.total_count += 1  # 把右边计算出来的结果保存到 total_count + 变量中，方便后面的代码继续复用
            self._purge_expired_locked()  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行

            stored = self._cache.get(key)  # 把右边计算出来的结果保存到 stored 变量中，方便后面的代码继续复用
            if stored is None:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                self.miss_count += 1  # 把右边计算出来的结果保存到 miss_count + 变量中，方便后面的代码继续复用
                return LocalCacheEntry(hit=False, value=None)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

            # 命中后要移动到尾部，保持 LRU 顺序。
            self._cache.move_to_end(key)  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
            self.hit_count += 1  # 把右边计算出来的结果保存到 hit_count + 变量中，方便后面的代码继续复用

            if stored.value == self._empty_marker:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                return LocalCacheEntry(hit=True, value=None)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
            return LocalCacheEntry(hit=True, value=stored.value)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    def get(self, key: Any) -> Optional[Any]:  # 定义函数 get，把一段可以复用的逻辑单独封装起来
        """兼容旧接口：只返回值，不返回命中状态。"""

        return self.get_entry(key).value  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    def set(self, key: Any, value: Any, ttl: Optional[int] = None) -> None:  # 定义函数 set，把一段可以复用的逻辑单独封装起来
        """写入缓存。

        `None` 会被转换成专用空值标记，这样上层仍能识别这是一次有效的负缓存。
        """

        if self.maxsize <= 0:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            self.logger.warning("本地缓存容量为 0，跳过写入", key=key)  # 记录一条警告日志，说明当前缓存容量配置不允许继续写入
            return  # 直接结束当前函数，并把空结果返回给调用方

        ttl_seconds = ttl if ttl is not None else self.ttl  # 把右边计算出来的结果保存到 ttl_seconds 变量中，方便后面的代码继续复用
        expire_at = self._now() + max(ttl_seconds, 1)  # 把右边计算出来的结果保存到 expire_at 变量中，方便后面的代码继续复用
        stored_value = self._empty_marker if value is None else value  # 把右边计算出来的结果保存到 stored_value 变量中，方便后面的代码继续复用

        with self._lock:  # 以上下文管理的方式使用资源，离开代码块时会自动释放或关闭
            self._purge_expired_locked()  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
            self._cache[key] = _StoredValue(value=stored_value, expire_at=expire_at)  # 把右边计算出来的结果保存到 _cache[key] 变量中，方便后面的代码继续复用
            self._cache.move_to_end(key)  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
            self._ensure_capacity_locked()  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行

    def delete(self, key: Any) -> None:  # 定义函数 delete，把一段可以复用的逻辑单独封装起来
        """删除单个缓存键。"""

        with self._lock:  # 以上下文管理的方式使用资源，离开代码块时会自动释放或关闭
            self._cache.pop(key, None)  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行

    def touch(self, key: Any, ttl: Optional[int] = None) -> bool:  # 定义函数 touch，把一段可以复用的逻辑单独封装起来
        """刷新某个 key 的过期时间。"""

        ttl_seconds = ttl if ttl is not None else self.ttl  # 把右边计算出来的结果保存到 ttl_seconds 变量中，方便后面的代码继续复用
        with self._lock:  # 以上下文管理的方式使用资源，离开代码块时会自动释放或关闭
            self._purge_expired_locked()  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
            stored = self._cache.get(key)  # 把右边计算出来的结果保存到 stored 变量中，方便后面的代码继续复用
            if stored is None:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                return False  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
            stored.expire_at = self._now() + max(ttl_seconds, 1)  # 把右边计算出来的结果保存到 stored.expire_at 变量中，方便后面的代码继续复用
            self._cache.move_to_end(key)  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
            return True  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    def clear(self) -> None:  # 定义函数 clear，把一段可以复用的逻辑单独封装起来
        """清空本地缓存。"""

        with self._lock:  # 以上下文管理的方式使用资源，离开代码块时会自动释放或关闭
            self._cache.clear()  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行

    def get_status(self) -> Dict[str, Any]:  # 定义函数 get_status，把一段可以复用的逻辑单独封装起来
        """返回基础监控信息。"""

        with self._lock:  # 以上下文管理的方式使用资源，离开代码块时会自动释放或关闭
            self._purge_expired_locked()  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
            hit_rate = (  # 把右边计算出来的结果保存到 hit_rate 变量中，方便后面的代码继续复用
                round(self.hit_count / self.total_count * 100, 2)  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                if self.total_count  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                else 0.0  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
            )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
            return {  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
                "max_capacity": self.maxsize,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                "current_size": len(self._cache),  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                "hit_count": self.hit_count,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                "miss_count": self.miss_count,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                "total_requests": self.total_count,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                "hit_rate": hit_rate,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                "default_ttl": self.ttl,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
            }  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级


# 全局单例：供多级缓存协调器复用。
local_cache = LocalLRUCache(maxsize=1000, ttl=300)  # 把右边计算出来的结果保存到 local_cache 变量中，方便后面的代码继续复用
