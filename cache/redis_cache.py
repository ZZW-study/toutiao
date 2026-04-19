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

from configs.redis import RedisConfig, redis_client
from utils.logger import get_logger
from utils.singleflight import singleflight

logger = get_logger(name="RedisCache")
T = TypeVar("T")

# 生成缓存 key 时需要跳过的参数名和参数类型。
# 这些是运行时上下文，每次请求都不同，但业务参数相同应该命中同一缓存。
# 例子：get_user(user_id=1, db=session_A) 和 get_user(user_id=1, db=session_B)
# 如果不跳过 db，两次请求的 key 不同，缓存无法命中
# 跳过后，key 都是 "user:user_id=1"，第二次命中缓存
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
    """将业务对象转换为可 JSON 序列化的纯 Python 结构。

    为什么需要这个函数？
    - 业务层经常返回 Pydantic 模型、dataclass、datetime、UUID、Enum 等
    - Redis 只能存储字符串（或二进制数据），不能直接存储这些复杂对象
    - 必须先转换为 dict/list/str/int/float/bool/None，再通过 json.dumps 变成字符串

    json.dumps 的限制：
    - json.dumps 会递归处理所有嵌套层级，但只能处理基本类型
    - json.dumps({"a": [1, 2, {"b": 3}]})  ✅ 成功，嵌套 dict/list 没问题
    - json.dumps({"time": datetime(2024, 1, 1)})  ❌ 报错，datetime 不是基本类型
    - json.dumps({"user": User(name="a")})  ❌ 报错，dataclass 不是基本类型

    本函数的作用：
    - 递归遍历对象的所有属性（套娃），把复杂类型转成基本类型
    - datetime → "2024-01-01T00:00:00"
    - dataclass → {"name": "a", ...}
    - Enum → 枚举值
    - 转换后的结果再交给 json.dumps 就能成功了

    如果遇到 ORM 对象或其他无法转换的类型，主动抛出 TypeError，
    迫使调用方先手动转换成可缓存的形式。
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
        # dataclass 实例转为 dict 后递归处理，如 User(name="a", age=1) → {"name": "a", "age": 1}
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
    """根据value 生成缓存 key 。

    为什么需要这个函数？
    - 缓存 key 必须稳定，相同参数要生成相同的 key
    - 函数参数可能是各种类型（datetime、Pydantic 模型、dataclass 等）
    - 需要把它们转成可序列化的形式，再拼成缓存 key

    和 _normalize_cache_value 的区别：
    - _normalize_cache_value：处理函数返回值（要存入 Redis 的数据）
    - _normalize_key_component：处理函数参数（要生成缓存 key）
    - 参数中可能包含 db、session、request 等运行时上下文，需要跳过，不能参与 key 计算

    例子：
    - get_user(user_id=1, db=session) → key 片段只包含 user_id=1，跳过 db
    - get_user(user_id=1, db=另一个session) → key 片段相同，命中缓存
    """
    if isinstance(value, _IGNORED_ARG_TYPES):
        return None  # 跳过 session、request 等运行时上下文，不参与 key 计算

    if value is None or isinstance(value, (str, int, float, bool)):
        return value  # 基本类型直接返回

    if isinstance(value, (datetime, date)):
        return value.isoformat()  # datetime → "2024-01-01T00:00:00"

    if isinstance(value, UUID):
        return str(value)  # UUID → "a1b2c3d4-..."

    if isinstance(value, Enum):
        return _normalize_key_component(value.value)  # Enum.ACTIVE → 1

    if isinstance(value, BaseModel):
        return _normalize_key_component(value.model_dump(mode="json", exclude_none=True))

    if is_dataclass(value):
        return _normalize_key_component(asdict(value))  # dataclass → dict

    # dict 按 key 排序并跳过运行时上下文字段（如 db、session）
    if isinstance(value, dict):
        return {
            str(key): _normalize_key_component(item)
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))
            if str(key) not in _IGNORED_KEYWORD_NAMES  # 过滤掉 db、session 等
        }

    if isinstance(value, (list, tuple, set)):
        return [_normalize_key_component(item) for item in value]

    # 对非标准对象，优先尝试 __cache_key__ 方法
    if hasattr(value, "__cache_key__"):
        return _normalize_key_component(value.__cache_key__())

    # 尝试提取公开属性（非 _ 开头的属性）
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

    # 无法提取属性，返回类型名作为 key
    return f"{value.__class__.__module__}.{value.__class__.__qualname__}"


class CacheUtil:
    """Redis 缓存基础工具。

    为什么不需要锁？
    - Redis 命令是原子的：get/set 等操作不会被其他命令打断，要么是不执行，要么就执行完
    1. Redis 命令的真正执行发生在 Redis 服务器，不是客户端
    当你调用 redis_client.get('key') 时：
    Python 线程将命令（如 GET key\r\n）通过网络发送到 Redis 服务器。
    Redis 服务器在自己的进程中（独立于你的 Python 进程）接收命令、执行、返回结果。
    Python 线程随后阻塞等待响应（或异步等待）。
    即使你的 Python 线程在发送命令后、收到响应前被操作系统挂起（时间片用完），Redis 服务器仍然会继续执行那个命令，并且执行是原子的。
    2. 命令的原子性由 Redis 服务器保证，与客户端线程调度无关
    Redis 服务器的命令执行是 单线程 的（忽略 6.0+ 的 I/O 多线程，那不影响命令处理的原子性）。
    一旦 Redis 开始处理 GET 或 SET，它会 完全执行完该命令，期间不会切换到其他客户端发来的命令。
    所以：
    要么命令还没开始执行（还在网络缓冲区中），
    要么命令已经完整执行完并准备返回结果。
    不存在“执行一半被操作系统调度打断”的情况，因为 Redis 自己控制执行流程，不依赖客户端线程的调度。
    3. 客户端线程时间片到会发生什么？
    时间点	行为
    命令尚未发送到 Redis	线程被挂起，发送延迟，但命令本身还没开始。
    命令已经发送，等待响应	线程被挂起，Redis 服务器依然会执行命令并准备好结果。当你的线程重新获得 CPU 时，它会继续读取 socket 缓冲区中的响应。
    命令执行完成，响应已回到客户端 socket 缓冲区	线程挂起也无影响，醒来后直接读取结果。
    关键在于：命令在 Redis 上的执行是原子的，不受客户端线程调度影响。

    - 连接池已处理并发：多协程并发获取连接，连接池内部有锁
    - Python 协程是协作式调度：await 会主动让出控制权，但 Redis 操作本身原子执行
    - 对比本地缓存：本地缓存的 OrderedDict 操作不是原子的，需要 RLock 保护
    """

    @staticmethod
    async def get(key: str) -> Optional[str]:
        """从 Redis 读取原始缓存值，返回pyload"""
        try:
            return await redis_client.get(key)
        except Exception:
            logger.warning("Redis 读取失败，降级为未命中", key=key, exc_info=True)
            return None

    @staticmethod
    async def get_entry(key: str) -> CacheReadResult:
        """读取并解析缓存值，返回带命中状态的结果。

        存储格式: {"v": 1, "e": true/false, "val": ...}
        - v: 版本号
        - e: 是否为空值（负缓存）
        - val: 实际数据
        """
        raw = await CacheUtil.get(key)
        if raw is None:
            return CacheReadResult(hit=False, value=None)

        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Redis 缓存值不是合法 JSON，按未命中处理")
            return CacheReadResult(hit=False, value=None)
        return CacheReadResult(hit=True, value=payload)


    @staticmethod
    async def set(key: str, value: Any, ex: Optional[int] = 3600) -> bool:
        """把业务值写入 Redis。

        自动包装成标准格式存入，适合普通缓存场景。
        输入: {"name": "张三"}
        存入: {"v":1,"e":false,"val":{"name":"张三"}}

        存储格式: {"v": 1, "e": true/false, "val": ...}
        - v: 版本号
        - e: 是否为空值（负缓存）
        - val: 实际数据
        """
        try:
            payload = {
                "v": 1,
                "e": value is None,
                "val": None if value is None else _normalize_cache_value(value),
            }
            serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))  # 去掉所有空格，生成最小体积的压缩 JSON
            if ex is None:
                await redis_client.set(key, serialized)
            else:
                await redis_client.set(key, serialized, ex=max(ex, 1))
            return True
        except TypeError:
            logger.warning("跳过不支持序列化的缓存值", key=key, exc_info=True)
            return False
        except Exception:
            logger.warning("Redis 写入失败", key=key, exc_info=True)
            return False

    @staticmethod
    async def set_raw_json(key: str, payload: dict[str, Any], ex: Optional[int] = None) -> bool:
        """直接写入已构建好的 payload，不自动包装。

        和 set() 的区别：
        - set(): 输入业务值，自动包装成 {"v":1,"e":...,"val":...}
        - set_raw_json(): 输入已构建好的 payload，直接序列化存入

        用途：stale-while-revalidate 需要存储 mode、expire_at 等额外字段，
        如果用 set() 包装，这些字段会被包在 val 里面，解析时会很麻烦。

        例子：
        payload = {"mode": "stale", "expire_at": 123456, "value": {...}}
        set_raw_json 直接存入这个 payload，不额外包装
        """
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

    # 计算 JSON 字符串的 MD5 哈希值。
    # MD5 不是用于安全加密，而是将任意长度的参数内容压缩为固定长度（32 个十六进制字符），避免缓存 key 过长。
    # 例如：参数内容可能很长（如包含大文本），直接拼接到 key 中会超出 Redis key 长度限制（通常 512 字节）且难以阅读。
    digest = hashlib.md5(serialized.encode("utf-8")).hexdigest()

    # 组装最终的缓存 key：前缀 + 冒号 + 哈希值。
    # 前缀用于区分不同业务或函数（如 "user:profile"、"order:list"），便于按前缀批量删除或观察。
    # 冒号是 Redis 键名的常见分隔符，支持按前缀扫描。
    # 最终 key 示例：user:profile:a1b2c3d4e5f6...
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
    """标准读穿缓存装饰器。

    和 logic_cache 的区别：
    ┌─────────────────┬────────────────────┬─────────────────────────┐
    │                 │ cache              │ logic_cache             │
    ├─────────────────┼────────────────────┼─────────────────────────┤
    │ 过期策略        │ 单一过期时间       │ 软过期 + 硬过期         │
    │ 过期后行为      │ 同步回源，阻塞请求 │ 返回旧值 + 后台刷新     │
    │ 请求延迟        │ 过期时可能阻塞     │ 永不阻塞                │
    │ 数据新鲜度      │ 要么新要么过期     │ 可能返回几秒旧值        │
    │ 适用场景        │ 通用缓存           │ 热点数据、读多写少      │
    │ 例子            │ 用户信息、订单     │ 分类、配置、榜单        │
    └─────────────────┴────────────────────┴─────────────────────────┘

    流程：
    请求 → 查缓存 → 命中？返回 : 查DB → 写缓存 → 返回
    """

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
                is_empty = _looks_like_empty(result)
                # 空值用较短的过期时间，防止缓存穿透
                # 如果空值缓存时间太长，万一后来数据库中真的写入了该数据（例如用户注册了之前不存在的 ID），缓存仍然返回空，导致数据不一致
                ttl = empty_expire if is_empty else _ttl_with_jitter(expire)
                await CacheUtil.set(cache_key, None if is_empty else result, ex=ttl)
                return None if is_empty else result

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
    流程：
    请求 → 查缓存 → 新鲜？返回 : 软过期？返回旧值+后台刷新 : 同步回源

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
    """写入 stale-while-revalidate payload。

    stale-while-revalidate 是一种缓存策略，允许在缓存过期后返回旧值并后台刷新：

    时间线：
    ┌─────────────────────────────────────────────────────────────┐
    │  0s        expire_seconds         hard_expire_seconds       │
    │  ├──────────┼─────────────────────────┼──────────►          │
    │  │  新鲜    │   过期但可用            │   完全过期           │
    │  │          │   返回旧值+后台刷新      │   同步回源           │
    └──┴──────────┴─────────────────────────┴──────────┘

    三种状态：
    - 新鲜期（0 ~ expire_seconds）：直接返回缓存
    - 软过期（expire_seconds ~ hard_expire_seconds）：返回旧值 + 后台异步刷新（把值更新为数据库新的值）
    - 硬过期（> hard_expire_seconds）：同步回源查询

    好处：热点数据永远不阻塞用户请求，适合分类、配置等"读多写少"的数据。
    """
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
