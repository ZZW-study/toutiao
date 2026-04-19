"""Redis 缓存封装。

重写后的实现遵循两个原则：

1. 缓存层只处理"明确可序列化"的数据，不再偷偷把复杂对象 `default=str`。
2. 缓存 key 必须稳定、可推导，不能因为忽略复杂参数而产生错误复用。
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import random
import time
from dataclasses import asdict, dataclass, is_dataclass
from datetime import date, datetime
from enum import Enum
from functools import wraps
from typing import Any, Callable, Coroutine, Iterable, Optional, TypeVar
from uuid import UUID

from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.requests import Request
from starlette.responses import Response

from cache.constants import EMPTY_CACHE_FLAG
from configs.redis import RedisConfig, redis_client
from utils.logger import get_logger
from utils.singleflight import singleflight

logger = get_logger(name="RedisCache")
T = TypeVar("T")

# 生成缓存 key 时需要跳过的参数名和参数类型。
_IGNORED_KEYWORD_NAMES = {"db", "session", "request", "response"}
_IGNORED_ARG_TYPES = (AsyncSession, Request, Response)


@dataclass(slots=True)
class CacheReadResult:
    """Redis 读取结果。

    `hit=True` 时，即使 value 为 `None`，也表示命中了负缓存。
    """

    hit: bool
    value: Any = None


def _looks_like_empty(value: Any) -> bool:
    """判断返回值是否应当写成负缓存。"""
    return value is None or (isinstance(value, (list, dict, set, tuple)) and not value)


def _normalize_cache_value(value: Any) -> Any:
    """把业务值转换成稳定的 JSON 值。

    这里只接受"可以明确恢复语义"的数据类型。
    如果传入 ORM 或其他复杂对象，会主动报错，让业务层显式决定怎么缓存。
    """
    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, Enum):
        return _normalize_cache_value(value.value)

    if isinstance(value, BaseModel):
        return _normalize_cache_value(value.model_dump(mode="json"))

    if is_dataclass(value):
        return _normalize_cache_value(asdict(value))

    # dict 按 key 排序后递归归一化，保证相同内容产生相同序列化结果。
    if isinstance(value, dict):
        return {
            str(key): _normalize_cache_value(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
        }

    if isinstance(value, (list, tuple, set)):
        return [_normalize_cache_value(item) for item in value]

    raise TypeError(
        f"缓存层不支持直接序列化 {type(value)!r}，"
        "请先在业务层转换成 dict/list/基础类型。"
    )


def _normalize_key_component(value: Any) -> Any:
    """把函数参数转换成稳定的 key 片段。"""
    if isinstance(value, _IGNORED_ARG_TYPES):
        return None

    if value is None or isinstance(value, (str, int, float, bool)):
        return value

    if isinstance(value, (datetime, date)):
        return value.isoformat()

    if isinstance(value, UUID):
        return str(value)

    if isinstance(value, Enum):
        return _normalize_key_component(value.value)

    if isinstance(value, BaseModel):
        return _normalize_key_component(value.model_dump(mode="json", exclude_none=True))

    if is_dataclass(value):
        return _normalize_key_component(asdict(value))

    # dict 按 key 排序并跳过运行时上下文字段。
    if isinstance(value, dict):
        return {
            str(key): _normalize_key_component(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            if str(key) not in _IGNORED_KEYWORD_NAMES
        }

    if isinstance(value, (list, tuple, set)):
        return [_normalize_key_component(item) for item in value]

    # 对非标准对象，优先尝试公开字段；如果没有，再回退到稳定类型名。
    if hasattr(value, "__cache_key__"):
        return _normalize_key_component(value.__cache_key__())

    public_attrs = {
        key: _normalize_key_component(item)
        for key, item in vars(value).items()
        if not key.startswith("_")
    } if hasattr(value, "__dict__") else {}

    if public_attrs:
        return {
            "__type__": f"{value.__class__.__module__}.{value.__class__.__qualname__}",
            "attrs": public_attrs,
        }

    return f"{value.__class__.__module__}.{value.__class__.__qualname__}"


def _wrap_standard_payload(value: Any) -> str:
    """标准缓存值序列化。

    标准 payload 的好处是：
    - 能明确表示负缓存。
    - 后续如果扩展版本字段，也不会和旧裸 JSON 混淆。
    """
    payload = {
        "version": 1,
        "empty": value is None,
        "value": None if value is None else _normalize_cache_value(value),
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def _unwrap_standard_payload(raw: str) -> CacheReadResult:
    """解析 Redis 中的标准缓存值。

    兼容旧格式：
    - 旧的空值哨兵字符串。
    - 旧版本直接 `json.dumps(value)` 的裸 JSON。
    """
    if raw == EMPTY_CACHE_FLAG:
        return CacheReadResult(hit=True, value=None)

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Redis 缓存值不是合法 JSON，按未命中处理")
        return CacheReadResult(hit=False, value=None)

    # stale-while-revalidate 使用单独的 payload 协议，交给 `logic_cache` 自己解析。
    if isinstance(payload, dict) and payload.get("mode") == "stale":
        return CacheReadResult(hit=False, value=None)

    if isinstance(payload, dict) and payload.get("version") == 1 and "empty" in payload:
        return CacheReadResult(hit=True, value=None if payload["empty"] else payload.get("value"))

    # 兼容历史裸 JSON 数据，读取后直接作为有效缓存值返回。
    return CacheReadResult(hit=True, value=payload)


class CacheUtil:
    """Redis 缓存基础工具。"""

    EMPTY_CACHE_FLAG = EMPTY_CACHE_FLAG

    @staticmethod
    async def get(key: str) -> Optional[str]:
        """从 Redis 读取原始缓存值。"""
        try:
            return await redis_client.get(key)
        except Exception:
            logger.warning("Redis 读取失败，降级为未命中", key=key, exc_info=True)
            return None

    @staticmethod
    async def get_entry(key: str) -> CacheReadResult:
        """读取并解析标准缓存结构，返回带命中状态的结果。"""
        raw = await CacheUtil.get(key)
        if raw is None:
            return CacheReadResult(hit=False, value=None)
        return _unwrap_standard_payload(raw)

    @staticmethod
    async def get_json(key: str) -> Optional[Any]:
        """读取缓存并直接返回解析后的业务值。"""
        return (await CacheUtil.get_entry(key)).value

    @staticmethod
    async def set(key: str, value: Any, ex: Optional[int] = 3600) -> bool:
        """把业务值写入 Redis，并按统一协议完成序列化。"""
        try:
            payload = _wrap_standard_payload(None if value is None else value)
            if ex is None:
                await redis_client.set(key, payload)
            else:
                # ex 最小取 1 秒，防止写入即过期。
                await redis_client.set(key, payload, ex=max(ex, 1))
            return True
        except TypeError:
            # 明确记录不可缓存的数据类型，让问题暴露在日志里而不是悄悄污染缓存。
            logger.warning("跳过不支持序列化的缓存值", key=key, exc_info=True)
            return False
        except Exception:
            logger.warning("Redis 写入失败", key=key, exc_info=True)
            return False

    @staticmethod
    async def set_raw_json(key: str, payload: dict[str, Any], ex: Optional[int] = None) -> bool:
        """供 stale-while-revalidate 使用的底层 JSON 写入。"""
        try:
            serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
            if ex is None:
                await redis_client.set(key, serialized)
            else:
                await redis_client.set(key, serialized, ex=max(ex, 1))
            return True
        except Exception:
            logger.warning("Redis JSON 写入失败", key=key, exc_info=True)
            return False

    @staticmethod
    async def delete(key: str) -> bool:
        """删除指定缓存键。"""
        try:
            await redis_client.delete(key)
            return True
        except Exception:
            logger.warning("Redis 删除失败", key=key, exc_info=True)
            return False

    @staticmethod
    async def exists(key: str) -> bool:
        """判断某个缓存键当前是否存在。"""
        try:
            return await redis_client.exists(key) == 1
        except Exception:
            return False

    @staticmethod
    async def is_available() -> bool:
        """通过 ping 检查 Redis 当前是否可用。"""
        try:
            return bool(await redis_client.ping())
        except Exception:
            return False

    @staticmethod
    async def close() -> None:
        """关闭 Redis 客户端及其底层连接池。"""
        try:
            await redis_client.close()
            await redis_client.connection_pool.disconnect()
        except Exception:
            logger.warning("关闭 Redis 连接失败", exc_info=True)


def generate_cache_key(prefix: str, args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:
    """生成稳定缓存 key。

    关键点：
    - 显式跳过 `db/request/response` 这类运行时上下文对象。
    - 结构化参数会被稳定序列化，而不是简单粗暴地忽略。
    """
    # 过滤掉运行时上下文参数，只保留业务参数。
    normalized_args = [
        _normalize_key_component(arg)
        for arg in args
        if not isinstance(arg, _IGNORED_ARG_TYPES)
    ]
    normalized_kwargs = {
        key: _normalize_key_component(value)
        for key, value in sorted(kwargs.items())
        if key not in _IGNORED_KEYWORD_NAMES
    }

    # 序列化后取 MD5，保证 key 长度可控且与参数内容一一对应。
    raw_payload = {"args": normalized_args, "kwargs": normalized_kwargs}
    serialized = json.dumps(raw_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    digest = hashlib.md5(serialized.encode("utf-8")).hexdigest()
    return f"{prefix}:{digest}"


def _ttl_with_jitter(expire: int) -> int:
    """为过期时间增加随机抖动，降低缓存雪崩风险。"""
    jitter = min(max(expire // 10, 1), RedisConfig.CACHE_RANDOM_OFFSET)
    return expire + random.randint(0, jitter)


def cache(
    key_prefix: str,
    expire: int = 3600,
    empty_expire: int = RedisConfig.EMPTY_CACHE_EXPIRE,
) -> Callable[[Callable[..., Coroutine[Any, Any, T]]], Callable[..., Coroutine[Any, Any, Optional[T]]]]:
    """标准读穿缓存装饰器。"""

    def decorator(
        func: Callable[..., Coroutine[Any, Any, T]]
    ) -> Callable[..., Coroutine[Any, Any, Optional[T]]]:
        """接收业务函数并返回带缓存能力的包装函数。"""

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Optional[T]:
            """执行标准读穿缓存流程，优先命中缓存，未命中时回源。"""
            cache_key = generate_cache_key(key_prefix, args, kwargs)

            cached = await CacheUtil.get_entry(cache_key)
            if cached.hit:
                return cached.value

            async def load_and_fill() -> Optional[T]:
                """真正执行原函数，并把结果写回缓存。"""

                # 并发场景下再次检查，避免重复查库。
                second_check = await CacheUtil.get_entry(cache_key)
                if second_check.hit:
                    return second_check.value

                result = await func(*args, **kwargs)
                # 空值用较短的过期时间，防止缓存穿透。
                ttl = empty_expire if _looks_like_empty(result) else _ttl_with_jitter(expire)
                await CacheUtil.set(cache_key, None if _looks_like_empty(result) else result, ex=ttl)
                return None if _looks_like_empty(result) else result

            # SingleFlight 合并并发请求；降级时直接执行原函数。
            try:
                return await singleflight.do(f"cache:{cache_key}", load_and_fill)
            except Exception:
                logger.warning("缓存装饰器降级为直接执行函数", key=cache_key, exc_info=True)
                return await func(*args, **kwargs)

        return wrapper

    return decorator


def logic_cache(
    key_prefix: str,
    expire_seconds: int = 3600,
) -> Callable[[Callable[..., Coroutine[Any, Any, T]]], Callable[..., Coroutine[Any, Any, Optional[T]]]]:
    """stale-while-revalidate 风格的热点缓存装饰器。

    适用场景：分类、配置、榜单等"读多写少且允许几秒旧值"的数据。
    """
    # 硬过期 = 软过期 3 倍或至少多 60 秒，确保后台刷新有足够时间窗口。
    hard_expire_seconds = max(expire_seconds * 3, expire_seconds + 60)

    def decorator(
        func: Callable[..., Coroutine[Any, Any, T]]
    ) -> Callable[..., Coroutine[Any, Any, Optional[T]]]:
        """接收业务函数并返回带热点缓存能力的包装函数。"""

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Optional[T]:
            """执行热点缓存读取流程，必要时触发后台刷新。"""
            cache_key = generate_cache_key(key_prefix, args, kwargs)
            raw = await CacheUtil.get(cache_key)
            now = int(time.time())

            if raw:
                try:
                    payload = json.loads(raw)
                    if payload.get("mode") == "stale":
                        value = None if payload.get("empty", False) else payload.get("value")
                        expire_at = int(payload.get("expire_at", 0))

                        # 软过期未到，直接返回。
                        if expire_at > now:
                            return value

                        # 软过期已到但硬过期未到：返回旧值并异步刷新。
                        async def refresh_task() -> None:
                            """在后台刷新过期热点缓存，避免阻塞当前请求。"""
                            try:
                                await singleflight.do(
                                    f"logic-refresh:{cache_key}",
                                    lambda: _refresh_logic_cache(
                                        cache_key=cache_key,
                                        func=func,
                                        args=args,
                                        kwargs=kwargs,
                                        expire_seconds=expire_seconds,
                                        hard_expire_seconds=hard_expire_seconds,
                                    ),
                                )
                            except Exception:
                                logger.warning("热点缓存后台刷新失败", key=cache_key, exc_info=True)

                        asyncio.create_task(refresh_task())
                        return value
                except json.JSONDecodeError:
                    logger.warning("热点缓存数据损坏，按未命中处理", key=cache_key)

            # 完全未命中或数据损坏，同步回源。
            result = await func(*args, **kwargs)
            await _write_logic_cache(cache_key, result, expire_seconds, hard_expire_seconds)
            return None if _looks_like_empty(result) else result

        return wrapper

    return decorator


async def _write_logic_cache(
    cache_key: str,
    result: Any,
    expire_seconds: int,
    hard_expire_seconds: int,
) -> None:
    """写入 stale-while-revalidate payload。"""
    payload = {
        "mode": "stale",
        "version": 1,
        "expire_at": int(time.time()) + expire_seconds,
        "empty": _looks_like_empty(result),
        "value": None if _looks_like_empty(result) else _normalize_cache_value(result),
    }
    await CacheUtil.set_raw_json(cache_key, payload, ex=hard_expire_seconds)


async def _refresh_logic_cache(
    cache_key: str,
    func: Callable[..., Coroutine[Any, Any, T]],
    args: Iterable[Any],
    kwargs: dict[str, Any],
    expire_seconds: int,
    hard_expire_seconds: int,
) -> None:
    """后台刷新热点缓存。"""
    result = await func(*args, **kwargs)
    await _write_logic_cache(cache_key, result, expire_seconds, hard_expire_seconds)
