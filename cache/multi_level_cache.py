"""多级缓存协调器。

职责边界：
- L1：本地进程内热点缓存，追求极低延迟。
- L2：Redis 共享缓存，承担跨进程复用。
- DB：最终数据源。

这次重写把之前“运行时再动态套装饰器”的写法改成了固定包装流程，
这样逻辑更直观，也更容易调试和测试。
"""

from __future__ import annotations  # 开启延迟解析类型注解，避免前向引用在导入阶段就被过早求值

from functools import wraps  # 从 functools 模块导入当前文件后续要用到的对象
from threading import RLock  # 从 threading 模块导入当前文件后续要用到的对象
from typing import Any, Callable, Coroutine, Optional, TypeVar  # 从 typing 模块导入当前文件后续要用到的对象

from cache.local_cache import local_cache  # 从 cache.local_cache 模块导入当前文件后续要用到的对象
from cache.redis_cache import CacheUtil, cache, generate_cache_key, logic_cache  # 从 cache.redis_cache 模块导入当前文件后续要用到的对象
from utils.logger import get_logger  # 从 utils.logger 模块导入当前文件后续要用到的对象
from utils.singleflight import singleflight  # 从 utils.singleflight 模块导入当前文件后续要用到的对象

NULL_CACHE_EXPIRE_SECONDS = 300  # 把这个常量值保存到 NULL_CACHE_EXPIRE_SECONDS 中，后面会作为固定配置反复使用

T = TypeVar("T")  # 把这个常量值保存到 T 中，后面会作为固定配置反复使用
logger = get_logger(name="MultiLevelCache")  # 把右边计算出来的结果保存到 logger 变量中，方便后面的代码继续复用


class MultiLevelCache:  # 定义 MultiLevelCache 类，用来把这一块相关的状态和行为组织在一起
    """多级缓存核心协调类。"""

    _instance_lock: RLock = RLock()  # 把右边计算出来的结果保存到 _instance_lock 变量中，方便后面的代码继续复用
    _instance: Optional["MultiLevelCache"] = None  # 把右边计算出来的结果保存到 _instance 变量中，方便后面的代码继续复用

    def __new__(cls, *args: Any, **kwargs: Any) -> "MultiLevelCache":  # 定义函数 __new__，把一段可以复用的逻辑单独封装起来
        """使用单例模式，保证进程内只维护一套多级缓存协调器。"""
        with cls._instance_lock:  # 以上下文管理的方式使用资源，离开代码块时会自动释放或关闭
            if cls._instance is None:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                cls._instance = super().__new__(cls)  # 把右边计算出来的结果保存到 _instance 变量中，方便后面的代码继续复用
                cls._instance.l1 = local_cache  # 把右边计算出来的结果保存到 _instance.l1 变量中，方便后面的代码继续复用
                cls._instance.l2 = CacheUtil  # 把右边计算出来的结果保存到 _instance.l2 变量中，方便后面的代码继续复用
        return cls._instance  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    async def get(  # 定义异步函数 get，调用它时通常需要配合 await 使用
        self,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        key: str,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        db_func: Optional[Callable[..., Coroutine[Any, Any, T]]] = None,  # 把右边计算出来的结果保存到 db_func 变量中，方便后面的代码继续复用
        *db_args: Any,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        **db_kwargs: Any,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    ) -> Optional[T]:  # 这一行开始一个新的代码块，下面缩进的内容都属于它
        """统一读取入口。

        读取顺序固定为 `L1 -> L2 -> DB`。
        这里用 `get_entry()` 来区分“未命中”和“负缓存命中”。
        """

        local_entry = self.l1.get_entry(key)  # 把右边计算出来的结果保存到 local_entry 变量中，方便后面的代码继续复用
        if local_entry.hit:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            return local_entry.value  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

        redis_entry = await self.l2.get_entry(key)  # 把右边计算出来的结果保存到 redis_entry 变量中，方便后面的代码继续复用
        if redis_entry.hit:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            # Redis 命中后同步回填本地缓存，后续请求直接走 L1。
            self.l1.set(  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                key,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                redis_entry.value,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                ttl=NULL_CACHE_EXPIRE_SECONDS if redis_entry.value is None else None,  # 把右边计算出来的结果保存到 ttl 变量中，方便后面的代码继续复用
            )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
            return redis_entry.value  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

        if db_func is None:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            return None  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

        async def load_and_fill() -> Optional[T]:  # 定义异步函数 load_and_fill，调用它时通常需要配合 await 使用
            # SingleFlight 内再做一次双检，避免并发回源时重复查询 DB。
            """在两级缓存都未命中时回源数据库，并把结果回填到缓存中。"""
            second_local = self.l1.get_entry(key)  # 把右边计算出来的结果保存到 second_local 变量中，方便后面的代码继续复用
            if second_local.hit:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                return second_local.value  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

            second_redis = await self.l2.get_entry(key)  # 把右边计算出来的结果保存到 second_redis 变量中，方便后面的代码继续复用
            if second_redis.hit:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                self.l1.set(  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                    key,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                    second_redis.value,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                    ttl=NULL_CACHE_EXPIRE_SECONDS if second_redis.value is None else None,  # 把右边计算出来的结果保存到 ttl 变量中，方便后面的代码继续复用
                )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
                return second_redis.value  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

            db_value = await db_func(*db_args, **db_kwargs)  # 把右边计算出来的结果保存到 db_value 变量中，方便后面的代码继续复用
            if db_value is None:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                await self.l2.set(key, None, ex=NULL_CACHE_EXPIRE_SECONDS)  # 等待这个异步操作完成，再继续执行后面的代码
                self.l1.set(key, None, ttl=NULL_CACHE_EXPIRE_SECONDS)  # 把右边计算出来的结果保存到 l1.set(key, None, ttl 变量中，方便后面的代码继续复用
                return None  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

            await self.l2.set(key, db_value)  # 等待这个异步操作完成，再继续执行后面的代码
            self.l1.set(key, db_value)  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
            return db_value  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

        return await singleflight.do(f"multi-cache:{key}", load_and_fill)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    async def delete(self, key: str) -> None:  # 定义异步函数 delete，调用它时通常需要配合 await 使用
        """统一删除两级缓存。"""

        await self.l2.delete(key)  # 等待这个异步操作完成，再继续执行后面的代码
        self.l1.delete(key)  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行

    async def refresh(self, key: str, value: Any, ttl: Optional[int] = None) -> None:  # 定义异步函数 refresh，调用它时通常需要配合 await 使用
        """主动刷新两级缓存。"""

        await self.l2.set(key, value, ex=ttl)  # 等待这个异步操作完成，再继续执行后面的代码
        self.l1.set(  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
            key,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
            value,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
            ttl=NULL_CACHE_EXPIRE_SECONDS if value is None else ttl,  # 把右边计算出来的结果保存到 ttl 变量中，方便后面的代码继续复用
        )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级


multi_level_cache = MultiLevelCache()  # 把右边计算出来的结果保存到 multi_level_cache 变量中，方便后面的代码继续复用


def multi_cache(  # 定义函数 multi_cache，把一段可以复用的逻辑单独封装起来
    key_prefix: str,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    expire: int = 3600,  # 把右边计算出来的结果保存到 expire 变量中，方便后面的代码继续复用
    hot: bool = False,  # 把右边计算出来的结果保存到 hot 变量中，方便后面的代码继续复用
) -> Callable[[Callable[..., Coroutine[Any, Any, T]]], Callable[..., Coroutine[Any, Any, Optional[T]]]]:  # 这一行开始一个新的代码块，下面缩进的内容都属于它
    """业务层便捷装饰器。

    `hot=True` 时使用 stale-while-revalidate。
    `hot=False` 时使用标准读穿缓存。
    """

    redis_decorator = logic_cache(key_prefix=key_prefix, expire_seconds=expire) if hot else cache(  # 把右边计算出来的结果保存到 redis_decorator 变量中，方便后面的代码继续复用
        key_prefix=key_prefix,  # 把右边计算出来的结果保存到 key_prefix 变量中，方便后面的代码继续复用
        expire=expire,  # 把右边计算出来的结果保存到 expire 变量中，方便后面的代码继续复用
    )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级

    def decorator(  # 定义函数 decorator，把一段可以复用的逻辑单独封装起来
        func: Callable[..., Coroutine[Any, Any, T]]  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    ) -> Callable[..., Coroutine[Any, Any, Optional[T]]]:  # 这一行开始一个新的代码块，下面缩进的内容都属于它
        """接收业务函数并返回带多级缓存能力的增强函数。"""
        redis_wrapped = redis_decorator(func)  # 把右边计算出来的结果保存到 redis_wrapped 变量中，方便后面的代码继续复用

        @wraps(func)  # 使用 wraps 装饰下面的函数或类，给它附加额外能力
        async def wrapper(*args: Any, **kwargs: Any) -> Optional[T]:  # 定义异步函数 wrapper，调用它时通常需要配合 await 使用
            """先查本地缓存，再执行 Redis 层包装后的读取逻辑。"""
            cache_key = generate_cache_key(key_prefix, args, kwargs)  # 把右边计算出来的结果保存到 cache_key 变量中，方便后面的代码继续复用

            local_entry = multi_level_cache.l1.get_entry(cache_key)  # 把右边计算出来的结果保存到 local_entry 变量中，方便后面的代码继续复用
            if local_entry.hit:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                return local_entry.value  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

            result = await redis_wrapped(*args, **kwargs)  # 把右边计算出来的结果保存到 result 变量中，方便后面的代码继续复用
            multi_level_cache.l1.set(  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                cache_key,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                result,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                ttl=NULL_CACHE_EXPIRE_SECONDS if result is None else expire,  # 把右边计算出来的结果保存到 ttl 变量中，方便后面的代码继续复用
            )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
            return result  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

        return wrapper  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    return decorator  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束


# 兼容旧拼写，避免现有导入立刻失效。
MutiLevelCache = MultiLevelCache  # 把右边计算出来的结果保存到 MutiLevelCache 变量中，方便后面的代码继续复用
