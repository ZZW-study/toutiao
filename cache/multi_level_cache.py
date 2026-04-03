"""
多级缓存协调器（L1本地+L2Redis+DB兜底）
核心职责：
1. 标准读取链路：本地缓存(L1) → Redis缓存(L2) → 数据库(DB)
2. 自动回写机制：Redis/DB命中后异步回写本地缓存，极致提升后续查询性能
3. 全链路防护：缓存穿透(空值缓存)、雪崩(随机TTL)、击穿(SingleFlight+分布式锁+双检锁)
4. 数据一致性保障：统一写入/删除/刷新两级缓存，保证数据最终一致
5. 高可用降级：Redis异常自动降级，不阻塞主业务流程
"""
import asyncio
from typing import Any,Optional,TypeVar,Callable,Coroutine
from functools import wraps
from threading import RLock

from utils.logger import get_logger
from cache.local_cache import local_cache
from utils.singleflight import singleflight
from cache.redis_cache import generate_cache_key,logic_cache,cache,CacheUtil

# 空值缓存过期时间（秒），用于防止缓存穿透
NULL_CACHE_EXPIRE_SECONDS = 300  # 5分钟

T = TypeVar("T")
logger = get_logger(name="MultiLevelCache")

class MutiLevelCache:
    """
    多级缓存调度核心类
    【层级说明】
    1. L1 = local_cache  ：内存级缓存，最低延迟，90%读请求命中
    2. L2 = redis_cache  ：分布式缓存，跨实例共享，大容量
    3. DB  ：数据库，最终数据兜底
    """
    _instance_lock: RLock = RLock()
    _instance: Optional["MutiLevelCache"] = None

    def __new__(cls,*args,**kwargs) ->"MutiLevelCache":
        """
        线程安全单例模式
        作用：保证全局只有一个多级缓存实例，避免资源重复创建
        """
        with cls._instance_lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                # 只在首次创建时设置属性，避免每次调用都重新赋值
                cls._instance.l1 = local_cache
                cls._instance.l2 = CacheUtil

        return cls._instance


    async def get(
            self,
            key: str,
            db_func: Optional[Callable[...,Coroutine[Any,Any,T]]] = None, 
# 第一个 ...：表示这个函数接收任意数量、任意类型的参数
# 第二个是返回值类型
# Coroutine[Any,Any,T]：异步协程类型（async def 函数的返回值）
# Any,Any：协程的发送值、异常类型都不限制
# T：泛型，代表协程最终返回的值类型（任意类型，由调用时决定）
            *db_args,
            **db_kwargs
) ->Optional["T"]:
        """
        多级缓存读取入口
        流程：L1 → L2 → DB → 异步回写两级缓存
        :param key: 缓存唯一键
        :param db_func: 缓存未命中时，执行的数据库查询异步函数
        :param db_args: 数据库函数位置参数
        :param db_kwargs: 数据库函数关键字参数
        """
        local_value = self.l1.get(key)
        if local_value is not None:
            logger.debug(f"[多级缓存] L1本地缓存命中 | key={key}")
            return local_value

        try:
            redis_value = await self.l2.get(key)
            if redis_value is not None:
                logger.debug(f"[多级缓存] L2 Redis缓存命中 | key={key}")
            # 异步回写L1：不阻塞当前请求，提升后续查询性能    
            asyncio.create_task(self.l1.set(key,redis_value))
            return redis_value
        
        except Exception as e:
            # Redis异常自动降级：不影响主业务，直接查询数据库
            logger.warning(f"[多级缓存] Redis异常，自动降级查询DB | key={key}, err={str(e)}")

         # ====================== 第三步：缓存未命中，查询数据库 ======================
        # 无数据库查询函数，直接返回None
        if not db_func:
            logger.debug(f"[多级缓存] 无DB查询函数，返回空 | key={key}")
            return None

        # ====================== SingleFlight：合并并发请求，防缓存击穿 ======================
        # 相同key的并发请求，只执行一次DB查询
        db_value = await singleflight.do(key=key,func=lambda:db_func(*db_args,**db_kwargs))

        # ====================== 第四步：DB查询成功，异步回写两级缓存 ======================
        if db_value is not None:
            logger.debug(f"[多级缓存] DB查询成功，异步回写缓存 | key={key}")
            asyncio.create_task(self.l2.set(key,db_value))
            self.l1.set(key,db_value)
        else:
            # db无数据，则缓存空值，防止缓存穿透
            logger.debug(f"[多级缓存] DB无数据，写入空值防穿透 | key={key}")
            asyncio.create_task(self.l2.set(key, None, ex=NULL_CACHE_EXPIRE_SECONDS))

        return db_value
    
    async def delete(self,key: str) ->None:
        """
        统一删除两级缓存
        作用：数据更新/删除时调用，保证多级缓存数据一致性
        策略：先删Redis → 再删本地缓存（避免脏数据）
        """
        await self.l2.delete(key)
        self.l1.delete(key)
        logger.info(f"[多级缓存] 两级缓存删除成功 | key={key}")

    async def refresh(self,key: str,value: Any,ttl: Optional[int] = None) ->None:
        """
        主动刷新两级缓存
        作用：热点数据预热、数据更新后主动推送新值
        逻辑：先删除旧缓存 → 再写入新缓存
        """
        await self.delete(key)
        await self.l2.set(key,value,ex=ttl)
        self.l1.set(key,value,ttl)
        logger.info(f"[多级缓存] 两级缓存刷新完成 | key={key}")

multi_level_cache = MutiLevelCache()  # 全局单例实例


# ====================== 业务便捷装饰器（无感知接入多级缓存） ======================
def multi_cache(key_prefix: str,expire: int = 3600,hot: bool = False):
    """
    多级缓存装饰器
    :param key_prefix: 缓存前缀
    :param expire: 过期时间
    :param hot: 是否热点数据 → True=逻辑过期缓存，False=通用缓存
    """
    def decorator(func: Callable[...,Coroutine[Any,Any,T]]):
        @wraps(func)
        async def wrapper(*args:Any,**kwargs:Any) ->Optional[T]:
            cache_key = generate_cache_key(key_prefix, args, kwargs)
            local_val = multi_level_cache.l1.get(cache_key)
            if local_val is not None:
                return local_val

            if hot:
                @logic_cache(key_prefix=key_prefix, expire_seconds=expire)
                async def _wrapped():
                    return await func(*args, **kwargs)
                result = await _wrapped()
            else:
                @cache(key_prefix=key_prefix, expire=expire)
                async def _wrapped():
                    return await func(*args, **kwargs)
                result = await _wrapped()

            if result is not None:
                multi_level_cache.l1.set(cache_key, result)
            return result
        return wrapper
    return decorator


