"""
Redis 分布式缓存封装
职责：作为二级缓存，与 LocalLRUCache 配对
"""
import json
import asyncio
import random
import uuid
import hashlib
import redis.asyncio as redis
from typing import Any, Callable, TypeVar, Optional, Coroutine, Dict
from functools import wraps
from datetime import datetime
from threading import RLock


from utils.logger import get_logger
from configs.redis_conf import redis_client, UNLOCK_SCRIPT,RedisConfig

logger = get_logger(name="RedisCache")
T = TypeVar("T")
# 全局统一空值标识
EMPTY_CACHE_FLAG = "__CACHE_EMPTY__"
# ====================== 缓存基础工具类 ======================
class CacheUtil:
    """静态缓存工具类：封装Redis所有基础操作，统一异常处理、序列化、空值处理"""
    # 空值缓存唯一标识：避免与业务数据冲突
    EMPTY_CACHE_FLAG = EMPTY_CACHE_FLAG

    @staticmethod
    async def get(key: str) -> Optional[str]:
        """
        获取字符串缓存
        :param key: 缓存键
        :return: 缓存值 / None（异常/无数据）
        """
        try:
            return await redis_client.get(key)
        except Exception as e:
            logger.error(f"[CacheUtil] 获取缓存失败 | key={key}", exc_info=True)
            return None

    @staticmethod
    async def get_json(key: str) -> Optional[Any]:
        """
        获取JSON缓存：自动反序列化，兼容空值、异常
        修复：统一数据类型，int/bool/dict 取出类型不变
        """
        data = await CacheUtil.get(key)
        if not data:
            return None

        # 命中空值标识，直接返回None
        if data == CacheUtil.EMPTY_CACHE_FLAG:
            return None

        try:
            # 自动反序列化，恢复原始数据类型
            return json.loads(data)
        except json.JSONDecodeError as e:
            logger.error(f"[CacheUtil] JSON反序列化失败 | key={key}", exc_info=True)
            return None

    @staticmethod
    async def set(
        key: str,
        value: Any,
        ex: int = 3600,
        ensure_ascii: bool = False
    ) -> bool:
        """
        设置缓存：**全类型兼容**，统一JSON序列化，空值特殊处理
        修复：int/bool/str 存入后类型丢失问题
        """
        try:
            # 空值处理：防止缓存穿透
            if value is None:
                value = CacheUtil.EMPTY_CACHE_FLAG
            else:
                # 所有数据统一JSON序列化，保证类型一致
                # default=str：兼容datetime/对象等无法序列化的类型
                value = json.dumps(value, ensure_ascii=ensure_ascii, default=str)

            # 写入Redis，设置过期时间
            await redis_client.set(key, value, ex=ex)
            return True
        except Exception as e:
            logger.error(f"[CacheUtil] 设置缓存失败 | key={key}", exc_info=True)
            return False

    @staticmethod
    async def delete(key: str) -> bool:
        """删除指定缓存（数据更新时必调用，保证数据一致性）"""
        try:
            await redis_client.delete(key)
            logger.info(f"[CacheUtil] 缓存删除成功 | key={key}")
            return True
        except Exception as e:
            logger.error(f"[CacheUtil] 删除缓存失败 | key={key}", exc_info=True)
            return False

    @staticmethod
    async def exists(key: str) -> bool:
        """判断缓存是否存在"""
        try:
            return await redis_client.exists(key) == 1
        except Exception:
            return False

    @staticmethod
    async def close() -> None:
        """
        关闭Redis连接池
        作用：服务关闭时调用，防止连接泄漏（FastAPI生命周期钩子使用）
        """
        try:
            await redis_client.close()
            await redis_client.connection_pool.disconnect()
            logger.info("[CacheUtil] Redis连接池已安全关闭")
        except Exception as e:
            logger.error("[CacheUtil] 关闭Redis连接失败", exc_info=True)

# ====================== 缓存Key生成工具======================
def generate_cache_key(prefix: str, args: tuple, kwargs: dict) -> str:
    """
    生成唯一业务缓存Key
    优化：1. 过滤无用参数 2. MD5哈希防止Key过长 3. 排序保证参数顺序不影响Key
    :param prefix: 业务前缀（如：user:info、order:detail）
    :return: 合法的Redis Key
    """
    # 过滤不需要参与生成Key的参数（self、Redis客户端、数据库连接等）
    filter_types = (redis.Redis, type(None), int, str, float, bool)
    key_parts = [prefix]

    # 处理位置参数
    for arg in args:
        if not isinstance(arg, filter_types):
            key_parts.append(str(arg))

    # 处理关键字参数（排序后拼接，保证顺序无关）
    for k, v in sorted(kwargs.items()):
        if not isinstance(v, filter_types):
            key_parts.append(f"{k}={v}")

    # 拼接原始Key
    raw_key = ":".join(key_parts)
    # 优化：Redis Key最大512字节，超长则MD5哈希处理
    if len(raw_key) > 128:
        raw_key = f"{prefix}:{hashlib.md5(raw_key.encode()).hexdigest()}"

    return raw_key

# ====================== 缓存装饰器（防穿透/雪崩/击穿） ======================
def cache(
    key_prefix: str,
    expire: int = 3600,
    empty_expire: int = RedisConfig.EMPTY_CACHE_EXPIRE,
    lock_expire: int = RedisConfig.LOCK_EXPIRE,
    max_retry: int = RedisConfig.MAX_RETRY,
):
    """
    通用异步缓存装饰器（高并发首选）
    防护机制：
    1. 空值缓存 → 防缓存穿透
    2. 随机过期时间 → 防缓存雪崩
    3. 分布式锁 + 双检锁 → 防缓存击穿
    4. 熔断机制 → Redis宕机直接查库，保护服务
    """
    def decorator(func: Callable[..., Coroutine[Any, Any, T]]):
        @wraps(func)  # 保留原函数名称、文档字符串，便于调试
        async def wrapper(*args: Any, **kwargs: Any) -> Optional[T]:
            # 1. 生成唯一缓存Key + 分布式锁Key
            cache_key = generate_cache_key(key_prefix, args, kwargs)
            lock_key = f"lock:{cache_key}"
            # 生成锁唯一标识：防止误删他人锁
            lock_value = str(uuid.uuid4())

            # ---------------- 熔断保护：Redis异常直接跳过缓存 ----------------
            if RedisConfig.CIRCUIT_BREAKER and not await redis_client.ping():
                logger.warning(f"[CacheDecorator] Redis熔断激活，直接执行函数 | key={cache_key}")
                return await func(*args, **kwargs)

            # ---------------- 第一步：查询缓存，命中直接返回 ----------------
            cache_data = await CacheUtil.get_json(cache_key)
            if cache_data is not None:
                logger.debug(f"[CacheDecorator] 缓存命中 | key={cache_key}")
                return cache_data

            # ---------------- 第二步：获取分布式锁（指数退避重试，防惊群） ----------------
            for attempt in range(max_retry):
                # SETNX：仅当Key不存在时设置，实现互斥锁
                lock_acquired = await redis_client.set(
                    lock_key, lock_value, nx=True, ex=lock_expire
                )

                if lock_acquired:
                    logger.debug(f"[CacheDecorator] 分布式锁获取成功 | key={lock_key}")
                    break

                # 指数退避 + 随机抖动：避免大量请求同时抢锁（惊群效应）
                sleep_time = (0.1 * (2 ** attempt)) + random.uniform(0, 0.1)
                await asyncio.sleep(sleep_time)
            else:
                # 重试次数耗尽，直接查询数据库
                logger.warning(f"[CacheDecorator] 锁获取失败，直接执行函数 | key={cache_key}")
                return await func(*args, **kwargs)

            try:
                # ---------------- 第三步：双检锁(抢锁失败后，再次校验缓存，抢到锁的已经写上了) ----------------
                cache_data = await CacheUtil.get_json(cache_key)
                if cache_data is not None:
                    return cache_data

                # ---------------- 第四步：缓存未命中，执行原始函数查库 ----------------
                result = await func(*args, **kwargs)

                # ---------------- 第五步：空值缓存（防穿透） ----------------
                if result is None or (isinstance(result, (list, dict)) and not result):
                    await CacheUtil.set(cache_key, None, ex=empty_expire)
                    return None

                # ---------------- 第六步：写入缓存（随机过期，防雪崩） ----------------
                final_expire = expire + random.randint(1, RedisConfig.CACHE_RANDOM_OFFSET)
                await CacheUtil.set(cache_key, result, ex=final_expire)
                logger.debug(f"[CacheDecorator] 缓存写入成功 | key={cache_key}")
                return result

            except Exception as e:
                logger.error(f"[CacheDecorator] 缓存执行异常 | key={cache_key}", exc_info=True)
                # 异常降级：直接返回原始函数结果，保证服务可用
                return await func(*args, **kwargs)

            finally:
                try:
                    await UNLOCK_SCRIPT(keys=[lock_key], args=[lock_value])
                except Exception as e:
                    if "NoScriptError" in str(type(e).__name__) or "NoScriptError" in str(e):
                        logger.warning(f"[CacheDecorator] Lua脚本未缓存，跳过释放锁 | key={lock_key}")
                    else:
                        logger.warning(f"[CacheDecorator] 释放锁异常 | key={lock_key}, error={e}")

        return wrapper
    return decorator

# ====================== 逻辑过期缓存装饰器（热点数据首选） ======================
def logic_cache(
    key_prefix: str,
    expire_seconds: int = 3600,
):
    """
    逻辑过期缓存（超高并发热点数据专用）
    核心原理：
    1. 缓存永久有效，不依赖Redis TTL
    2. 过期后立即返回旧数据，后台异步重建缓存
    3. 无阻塞、高性能，用户无等待
    适用场景：首页数据、商品详情、配置中心等热点数据
    """
    def decorator(func: Callable[..., Coroutine[Any, Any, T]]):
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Optional[T]:
            cache_key = generate_cache_key(key_prefix, args, kwargs)
            now = int(datetime.now().timestamp())

            # ---------------- 第一步：查询缓存 ----------------
            cache_data = await CacheUtil.get_json(cache_key)
            # 无缓存：首次查询，直接查库并写入
            if not cache_data:
                result = await func(*args, **kwargs)
                # 存储结构：数据 + 逻辑过期时间，即没有给Redis设置任何 ex 过期时间！ Redis里这条数据【永久有效，永远不会被删除】
                cache_value = {"data": result, "expire": now + expire_seconds}
                await CacheUtil.set(cache_key, cache_value)
                return result

            # ---------------- 第二步：缓存未过期，直接返回 ----------------
            if cache_data["expire"] > now:
                return cache_data["data"]

            # ---------------- 第三步：缓存过期，异步重建，立即返回旧数据 ----------------
            async def rebuild_task():
                """异步缓存重建任务（带分布式锁，防止并发重复查库）"""
                try:
                    await _rebuild_cache(cache_key, func, args, kwargs, expire_seconds)
                except Exception as e:
                    logger.error(f"[LogicCache] 缓存重建失败 | key={cache_key}", exc_info=True)

            # 创建后台任务
            asyncio.create_task(rebuild_task())
            # 核心：立即返回旧数据，用户无等待
            return cache_data["data"]

        # 缓存重建函数：带分布式锁
        async def _rebuild_cache(key: str, func: Callable, args: Any, kwargs: Any, expire: int):
            lock_key = f"lock:logic:{key}"
            lock_value = str(uuid.uuid4())

            # 获取互斥锁
            lock_acquired = await redis_client.set(lock_key, lock_value, nx=True, ex=5)
            if not lock_acquired:
                return

            try:
                # 双检：防止重复查询数据库
                cache = await CacheUtil.get_json(key)
                if cache and cache["expire"] > int(datetime.now().timestamp()):
                    return

                # 查库并更新缓存
                result = await func(*args, **kwargs)
                new_data = {
                    "data": result,
                    "expire": int(datetime.now().timestamp()) + expire
                }
                await CacheUtil.set(key, new_data)
                logger.info(f"[LogicCache] 缓存重建成功 | key={key}")

            finally:
                try:
                    await UNLOCK_SCRIPT(keys=[lock_key], args=[lock_value])
                except Exception as e:
                    if "NoScriptError" in str(type(e).__name__) or "NoScriptError" in str(e):
                        logger.warning(f"[LogicCache] Lua脚本未缓存，跳过释放锁 | key={lock_key}")
                    else:
                        logger.warning(f"[LogicCache] 释放锁异常 | key={lock_key}, error={e}")

        return wrapper
    return decorator

