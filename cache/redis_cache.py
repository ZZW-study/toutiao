"""Redis 缓存封装。

重写后的实现遵循两个原则：

1. 缓存层只处理“明确可序列化”的数据，不再偷偷把复杂对象 `default=str`。
2. 缓存 key 必须稳定、可推导，不能因为忽略复杂参数而产生错误复用。
"""

from __future__ import annotations  # 开启延迟解析类型注解，避免前向引用在导入阶段就被过早求值

import asyncio  # 导入 asyncio 模块，给当前文件后面的逻辑使用
import hashlib  # 导入 hashlib 模块，给当前文件后面的逻辑使用
import json  # 导入 json 模块，给当前文件后面的逻辑使用
import random  # 导入 random 模块，给当前文件后面的逻辑使用
import time  # 导入 time 模块，给当前文件后面的逻辑使用
from dataclasses import asdict, dataclass, is_dataclass  # 从 dataclasses 模块导入当前文件后续要用到的对象
from datetime import date, datetime  # 从 datetime 模块导入当前文件后续要用到的对象
from enum import Enum  # 从 enum 模块导入当前文件后续要用到的对象
from functools import wraps  # 从 functools 模块导入当前文件后续要用到的对象
from typing import Any, Callable, Coroutine, Iterable, Optional, TypeVar  # 从 typing 模块导入当前文件后续要用到的对象
from uuid import UUID  # 从 uuid 模块导入当前文件后续要用到的对象

from pydantic import BaseModel  # 从 pydantic 模块导入当前文件后续要用到的对象
from sqlalchemy.ext.asyncio import AsyncSession  # 从 sqlalchemy.ext.asyncio 模块导入当前文件后续要用到的对象
from starlette.requests import Request  # 从 starlette.requests 模块导入当前文件后续要用到的对象
from starlette.responses import Response  # 从 starlette.responses 模块导入当前文件后续要用到的对象

from cache.constants import EMPTY_CACHE_FLAG  # 从 cache.constants 模块导入当前文件后续要用到的对象
from configs.redis import RedisConfig, redis_client  # 从 configs.redis 模块导入当前文件后续要用到的对象
from utils.logger import get_logger  # 从 utils.logger 模块导入当前文件后续要用到的对象
from utils.singleflight import singleflight  # 从 utils.singleflight 模块导入当前文件后续要用到的对象

logger = get_logger(name="RedisCache")  # 把右边计算出来的结果保存到 logger 变量中，方便后面的代码继续复用
T = TypeVar("T")  # 把这个常量值保存到 T 中，后面会作为固定配置反复使用

_IGNORED_KEYWORD_NAMES = {"db", "session", "request", "response"}  # 把这个常量值保存到 _IGNORED_KEYWORD_NAMES 中，后面会作为固定配置反复使用
_IGNORED_ARG_TYPES = (AsyncSession, Request, Response)  # 把这个常量值保存到 _IGNORED_ARG_TYPES 中，后面会作为固定配置反复使用


@dataclass(slots=True)  # 使用 dataclass 装饰下面的函数或类，给它附加额外能力
class CacheReadResult:  # 定义 CacheReadResult 类，用来把这一块相关的状态和行为组织在一起
    """Redis 读取结果。

    `hit=True` 时，即使 value 为 `None`，也表示命中了负缓存。
    """

    hit: bool  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    value: Any = None  # 把右边计算出来的结果保存到 value 变量中，方便后面的代码继续复用


def _looks_like_empty(value: Any) -> bool:  # 定义函数 _looks_like_empty，把一段可以复用的逻辑单独封装起来
    """判断返回值是否应当写成负缓存。"""

    return value is None or (isinstance(value, (list, dict, set, tuple)) and not value)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束


def _normalize_cache_value(value: Any) -> Any:  # 定义函数 _normalize_cache_value，把一段可以复用的逻辑单独封装起来
    """把业务值转换成稳定的 JSON 值。

    这里只接受“可以明确恢复语义”的数据类型。
    如果传入 ORM 或其他复杂对象，会主动报错，让业务层显式决定怎么缓存。
    """

    if value is None or isinstance(value, (str, int, float, bool)):  # 开始判断当前条件是否成立，再决定后面该走哪个分支
        return value  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    if isinstance(value, (datetime, date)):  # 开始判断当前条件是否成立，再决定后面该走哪个分支
        return value.isoformat()  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    if isinstance(value, UUID):  # 开始判断当前条件是否成立，再决定后面该走哪个分支
        return str(value)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    if isinstance(value, Enum):  # 开始判断当前条件是否成立，再决定后面该走哪个分支
        return _normalize_cache_value(value.value)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    if isinstance(value, BaseModel):  # 开始判断当前条件是否成立，再决定后面该走哪个分支
        return _normalize_cache_value(value.model_dump(mode="json"))  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    if is_dataclass(value):  # 开始判断当前条件是否成立，再决定后面该走哪个分支
        return _normalize_cache_value(asdict(value))  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    if isinstance(value, dict):  # 开始判断当前条件是否成立，再决定后面该走哪个分支
        return {  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
            str(key): _normalize_cache_value(item)  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))  # 开始遍历可迭代对象里的每一项，并对每一项执行同样的处理
        }  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级

    if isinstance(value, (list, tuple, set)):  # 开始判断当前条件是否成立，再决定后面该走哪个分支
        return [_normalize_cache_value(item) for item in value]  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    raise TypeError(  # 主动抛出异常，让上层知道这里出现了需要处理的问题
        f"缓存层不支持直接序列化 {type(value)!r}，"  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        "请先在业务层转换成 dict/list/基础类型。"  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级


def _normalize_key_component(value: Any) -> Any:  # 定义函数 _normalize_key_component，把一段可以复用的逻辑单独封装起来
    """把函数参数转换成稳定的 key 片段。"""

    if isinstance(value, _IGNORED_ARG_TYPES):  # 开始判断当前条件是否成立，再决定后面该走哪个分支
        return None  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    if value is None or isinstance(value, (str, int, float, bool)):  # 开始判断当前条件是否成立，再决定后面该走哪个分支
        return value  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    if isinstance(value, (datetime, date)):  # 开始判断当前条件是否成立，再决定后面该走哪个分支
        return value.isoformat()  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    if isinstance(value, UUID):  # 开始判断当前条件是否成立，再决定后面该走哪个分支
        return str(value)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    if isinstance(value, Enum):  # 开始判断当前条件是否成立，再决定后面该走哪个分支
        return _normalize_key_component(value.value)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    if isinstance(value, BaseModel):  # 开始判断当前条件是否成立，再决定后面该走哪个分支
        return _normalize_key_component(value.model_dump(mode="json", exclude_none=True))  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    if is_dataclass(value):  # 开始判断当前条件是否成立，再决定后面该走哪个分支
        return _normalize_key_component(asdict(value))  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    if isinstance(value, dict):  # 开始判断当前条件是否成立，再决定后面该走哪个分支
        return {  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
            str(key): _normalize_key_component(item)  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
            for key, item in sorted(value.items(), key=lambda pair: str(pair[0]))  # 开始遍历可迭代对象里的每一项，并对每一项执行同样的处理
            if str(key) not in _IGNORED_KEYWORD_NAMES  # 开始判断当前条件是否成立，再决定后面该走哪个分支
        }  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级

    if isinstance(value, (list, tuple, set)):  # 开始判断当前条件是否成立，再决定后面该走哪个分支
        return [_normalize_key_component(item) for item in value]  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    # 对非标准对象，优先尝试公开字段；如果没有，再回退到稳定类型名。
    if hasattr(value, "__cache_key__"):  # 开始判断当前条件是否成立，再决定后面该走哪个分支
        return _normalize_key_component(value.__cache_key__())  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    public_attrs = {  # 把右边计算出来的结果保存到 public_attrs 变量中，方便后面的代码继续复用
        key: _normalize_key_component(item)  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        for key, item in vars(value).items()  # 开始遍历可迭代对象里的每一项，并对每一项执行同样的处理
        if not key.startswith("_")  # 开始判断当前条件是否成立，再决定后面该走哪个分支
    } if hasattr(value, "__dict__") else {}  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行

    if public_attrs:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
        return {  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
            "__type__": f"{value.__class__.__module__}.{value.__class__.__qualname__}",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
            "attrs": public_attrs,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        }  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级

    return f"{value.__class__.__module__}.{value.__class__.__qualname__}"  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束


def _wrap_standard_payload(value: Any) -> str:  # 定义函数 _wrap_standard_payload，把一段可以复用的逻辑单独封装起来
    """标准缓存值序列化。

    标准 payload 的好处是：
    - 能明确表示负缓存。
    - 后续如果扩展版本字段，也不会和旧裸 JSON 混淆。
    """

    payload = {  # 把右边计算出来的结果保存到 payload 变量中，方便后面的代码继续复用
        "version": 1,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        "empty": value is None,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        "value": None if value is None else _normalize_cache_value(value),  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    }  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束


def _unwrap_standard_payload(raw: str) -> CacheReadResult:  # 定义函数 _unwrap_standard_payload，把一段可以复用的逻辑单独封装起来
    """解析 Redis 中的标准缓存值。

    兼容旧格式：
    - 旧的空值哨兵字符串。
    - 旧版本直接 `json.dumps(value)` 的裸 JSON。
    """

    if raw == EMPTY_CACHE_FLAG:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
        return CacheReadResult(hit=True, value=None)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    try:  # 开始尝试执行可能出错的逻辑，如果报错就会转到下面的异常分支
        payload = json.loads(raw)  # 把右边计算出来的结果保存到 payload 变量中，方便后面的代码继续复用
    except json.JSONDecodeError:  # 如果上面 try 里的代码报错，就进入这个异常处理分支
        logger.warning("Redis 缓存值不是合法 JSON，按未命中处理")  # 记录一条日志，方便后续排查程序运行过程和定位问题
        return CacheReadResult(hit=False, value=None)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    if isinstance(payload, dict) and payload.get("mode") == "stale":  # 开始判断当前条件是否成立，再决定后面该走哪个分支
        # stale-while-revalidate 使用单独的 payload 协议，这里交给 `logic_cache` 自己解析。
        return CacheReadResult(hit=False, value=None)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    if isinstance(payload, dict) and payload.get("version") == 1 and "empty" in payload:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
        return CacheReadResult(hit=True, value=None if payload["empty"] else payload.get("value"))  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    # 兼容历史裸 JSON 数据，读取后直接作为有效缓存值返回。
    return CacheReadResult(hit=True, value=payload)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束


class CacheUtil:  # 定义 CacheUtil 类，用来把这一块相关的状态和行为组织在一起
    """Redis 缓存基础工具。"""

    EMPTY_CACHE_FLAG = EMPTY_CACHE_FLAG  # 把这个常量值保存到 EMPTY_CACHE_FLAG 中，后面会作为固定配置反复使用

    @staticmethod  # 使用 staticmethod 装饰下面的函数或类，给它附加额外能力
    async def get(key: str) -> Optional[str]:  # 定义异步函数 get，调用它时通常需要配合 await 使用
        """从 Redis 读取原始缓存值。"""
        try:  # 开始尝试执行可能出错的逻辑，如果报错就会转到下面的异常分支
            return await redis_client.get(key)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
        except Exception:  # 如果上面 try 里的代码报错，就进入这个异常处理分支
            logger.warning("Redis 读取失败，降级为未命中", key=key, exc_info=True)  # 记录一条日志，方便后续排查程序运行过程和定位问题
            return None  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    @staticmethod  # 使用 staticmethod 装饰下面的函数或类，给它附加额外能力
    async def get_entry(key: str) -> CacheReadResult:  # 定义异步函数 get_entry，调用它时通常需要配合 await 使用
        """读取并解析标准缓存结构，返回带命中状态的结果。"""
        raw = await CacheUtil.get(key)  # 把右边计算出来的结果保存到 raw 变量中，方便后面的代码继续复用
        if raw is None:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            return CacheReadResult(hit=False, value=None)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
        return _unwrap_standard_payload(raw)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    @staticmethod  # 使用 staticmethod 装饰下面的函数或类，给它附加额外能力
    async def get_json(key: str) -> Optional[Any]:  # 定义异步函数 get_json，调用它时通常需要配合 await 使用
        """读取缓存并直接返回解析后的业务值。"""
        return (await CacheUtil.get_entry(key)).value  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    @staticmethod  # 使用 staticmethod 装饰下面的函数或类，给它附加额外能力
    async def set(key: str, value: Any, ex: Optional[int] = 3600) -> bool:  # 定义异步函数 set，调用它时通常需要配合 await 使用
        """把业务值写入 Redis，并按统一协议完成序列化。"""
        try:  # 开始尝试执行可能出错的逻辑，如果报错就会转到下面的异常分支
            payload = _wrap_standard_payload(None if value is None else value)  # 把右边计算出来的结果保存到 payload 变量中，方便后面的代码继续复用
            if ex is None:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                await redis_client.set(key, payload)  # 等待这个异步操作完成，再继续执行后面的代码
            else:  # 如果前面的条件都不成立，就会走这个兜底分支
                await redis_client.set(key, payload, ex=max(ex, 1))  # 等待这个异步操作完成，再继续执行后面的代码
            return True  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
        except TypeError:  # 如果上面 try 里的代码报错，就进入这个异常处理分支
            # 这里明确记录不可缓存的数据类型，让问题暴露在日志里而不是悄悄污染缓存。
            logger.warning("跳过不支持序列化的缓存值", key=key, exc_info=True)  # 记录一条日志，方便后续排查程序运行过程和定位问题
            return False  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
        except Exception:  # 如果上面 try 里的代码报错，就进入这个异常处理分支
            logger.warning("Redis 写入失败", key=key, exc_info=True)  # 记录一条日志，方便后续排查程序运行过程和定位问题
            return False  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    @staticmethod  # 使用 staticmethod 装饰下面的函数或类，给它附加额外能力
    async def set_raw_json(key: str, payload: dict[str, Any], ex: Optional[int] = None) -> bool:  # 定义异步函数 set_raw_json，调用它时通常需要配合 await 使用
        """供 stale-while-revalidate 使用的底层 JSON 写入。"""

        try:  # 开始尝试执行可能出错的逻辑，如果报错就会转到下面的异常分支
            serialized = json.dumps(payload, ensure_ascii=False, separators=(",", ":"))  # 把右边计算出来的结果保存到 serialized 变量中，方便后面的代码继续复用
            if ex is None:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                await redis_client.set(key, serialized)  # 等待这个异步操作完成，再继续执行后面的代码
            else:  # 如果前面的条件都不成立，就会走这个兜底分支
                await redis_client.set(key, serialized, ex=max(ex, 1))  # 等待这个异步操作完成，再继续执行后面的代码
            return True  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
        except Exception:  # 如果上面 try 里的代码报错，就进入这个异常处理分支
            logger.warning("Redis JSON 写入失败", key=key, exc_info=True)  # 记录一条日志，方便后续排查程序运行过程和定位问题
            return False  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    @staticmethod  # 使用 staticmethod 装饰下面的函数或类，给它附加额外能力
    async def delete(key: str) -> bool:  # 定义异步函数 delete，调用它时通常需要配合 await 使用
        """删除指定缓存键。"""
        try:  # 开始尝试执行可能出错的逻辑，如果报错就会转到下面的异常分支
            await redis_client.delete(key)  # 等待这个异步操作完成，再继续执行后面的代码
            return True  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
        except Exception:  # 如果上面 try 里的代码报错，就进入这个异常处理分支
            logger.warning("Redis 删除失败", key=key, exc_info=True)  # 记录一条日志，方便后续排查程序运行过程和定位问题
            return False  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    @staticmethod  # 使用 staticmethod 装饰下面的函数或类，给它附加额外能力
    async def exists(key: str) -> bool:  # 定义异步函数 exists，调用它时通常需要配合 await 使用
        """判断某个缓存键当前是否存在。"""
        try:  # 开始尝试执行可能出错的逻辑，如果报错就会转到下面的异常分支
            return await redis_client.exists(key) == 1  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
        except Exception:  # 如果上面 try 里的代码报错，就进入这个异常处理分支
            return False  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    @staticmethod  # 使用 staticmethod 装饰下面的函数或类，给它附加额外能力
    async def is_available() -> bool:  # 定义异步函数 is_available，调用它时通常需要配合 await 使用
        """通过 ping 检查 Redis 当前是否可用。"""
        try:  # 开始尝试执行可能出错的逻辑，如果报错就会转到下面的异常分支
            return bool(await redis_client.ping())  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
        except Exception:  # 如果上面 try 里的代码报错，就进入这个异常处理分支
            return False  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    @staticmethod  # 使用 staticmethod 装饰下面的函数或类，给它附加额外能力
    async def close() -> None:  # 定义异步函数 close，调用它时通常需要配合 await 使用
        """关闭 Redis 客户端及其底层连接池。"""
        try:  # 开始尝试执行可能出错的逻辑，如果报错就会转到下面的异常分支
            await redis_client.close()  # 等待这个异步操作完成，再继续执行后面的代码
            await redis_client.connection_pool.disconnect()  # 等待这个异步操作完成，再继续执行后面的代码
        except Exception:  # 如果上面 try 里的代码报错，就进入这个异常处理分支
            logger.warning("关闭 Redis 连接失败", exc_info=True)  # 记录一条日志，方便后续排查程序运行过程和定位问题


def generate_cache_key(prefix: str, args: tuple[Any, ...], kwargs: dict[str, Any]) -> str:  # 定义函数 generate_cache_key，把一段可以复用的逻辑单独封装起来
    """生成稳定缓存 key。

    关键点：
    - 显式跳过 `db/request/response` 这类运行时上下文对象。
    - 结构化参数会被稳定序列化，而不是简单粗暴地忽略。
    """

    normalized_args = [  # 把右边计算出来的结果保存到 normalized_args 变量中，方便后面的代码继续复用
        _normalize_key_component(arg)  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        for arg in args  # 开始遍历可迭代对象里的每一项，并对每一项执行同样的处理
        if not isinstance(arg, _IGNORED_ARG_TYPES)  # 开始判断当前条件是否成立，再决定后面该走哪个分支
    ]  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
    normalized_kwargs = {  # 把右边计算出来的结果保存到 normalized_kwargs 变量中，方便后面的代码继续复用
        key: _normalize_key_component(value)  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        for key, value in sorted(kwargs.items())  # 开始遍历可迭代对象里的每一项，并对每一项执行同样的处理
        if key not in _IGNORED_KEYWORD_NAMES  # 开始判断当前条件是否成立，再决定后面该走哪个分支
    }  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级

    raw_payload = {"args": normalized_args, "kwargs": normalized_kwargs}  # 把右边计算出来的结果保存到 raw_payload 变量中，方便后面的代码继续复用
    serialized = json.dumps(raw_payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))  # 把右边计算出来的结果保存到 serialized 变量中，方便后面的代码继续复用
    digest = hashlib.md5(serialized.encode("utf-8")).hexdigest()  # 把右边计算出来的结果保存到 digest 变量中，方便后面的代码继续复用
    return f"{prefix}:{digest}"  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束


def _ttl_with_jitter(expire: int) -> int:  # 定义函数 _ttl_with_jitter，把一段可以复用的逻辑单独封装起来
    """为过期时间增加随机抖动，降低缓存雪崩风险。"""
    jitter = min(max(expire // 10, 1), RedisConfig.CACHE_RANDOM_OFFSET)  # 把右边计算出来的结果保存到 jitter 变量中，方便后面的代码继续复用
    return expire + random.randint(0, jitter)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束


def cache(  # 定义函数 cache，把一段可以复用的逻辑单独封装起来
    key_prefix: str,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    expire: int = 3600,  # 把右边计算出来的结果保存到 expire 变量中，方便后面的代码继续复用
    empty_expire: int = RedisConfig.EMPTY_CACHE_EXPIRE,  # 把右边计算出来的结果保存到 empty_expire 变量中，方便后面的代码继续复用
) -> Callable[[Callable[..., Coroutine[Any, Any, T]]], Callable[..., Coroutine[Any, Any, Optional[T]]]]:  # 这一行开始一个新的代码块，下面缩进的内容都属于它
    """标准读穿缓存装饰器。"""

    def decorator(  # 定义函数 decorator，把一段可以复用的逻辑单独封装起来
        func: Callable[..., Coroutine[Any, Any, T]]  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    ) -> Callable[..., Coroutine[Any, Any, Optional[T]]]:  # 这一行开始一个新的代码块，下面缩进的内容都属于它
        """接收业务函数并返回带缓存能力的包装函数。"""

        @wraps(func)  # 使用 wraps 装饰下面的函数或类，给它附加额外能力
        async def wrapper(*args: Any, **kwargs: Any) -> Optional[T]:  # 定义异步函数 wrapper，调用它时通常需要配合 await 使用
            """执行标准读穿缓存流程，优先命中缓存，未命中时回源。"""
            cache_key = generate_cache_key(key_prefix, args, kwargs)  # 把右边计算出来的结果保存到 cache_key 变量中，方便后面的代码继续复用

            cached = await CacheUtil.get_entry(cache_key)  # 把右边计算出来的结果保存到 cached 变量中，方便后面的代码继续复用
            if cached.hit:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                return cached.value  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

            async def load_and_fill() -> Optional[T]:  # 定义异步函数 load_and_fill，调用它时通常需要配合 await 使用
                """真正执行原函数，并把结果写回缓存。"""

                # 并发场景下再次检查，避免重复查库。
                second_check = await CacheUtil.get_entry(cache_key)  # 把右边计算出来的结果保存到 second_check 变量中，方便后面的代码继续复用
                if second_check.hit:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                    return second_check.value  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

                result = await func(*args, **kwargs)  # 把右边计算出来的结果保存到 result 变量中，方便后面的代码继续复用
                ttl = empty_expire if _looks_like_empty(result) else _ttl_with_jitter(expire)  # 把右边计算出来的结果保存到 ttl 变量中，方便后面的代码继续复用
                await CacheUtil.set(cache_key, None if _looks_like_empty(result) else result, ex=ttl)  # 等待这个异步操作完成，再继续执行后面的代码
                return None if _looks_like_empty(result) else result  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

            try:  # 开始尝试执行可能出错的逻辑，如果报错就会转到下面的异常分支
                return await singleflight.do(f"cache:{cache_key}", load_and_fill)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
            except Exception:  # 如果上面 try 里的代码报错，就进入这个异常处理分支
                logger.warning("缓存装饰器降级为直接执行函数", key=cache_key, exc_info=True)  # 记录一条日志，方便后续排查程序运行过程和定位问题
                return await func(*args, **kwargs)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

        return wrapper  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    return decorator  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束


def logic_cache(  # 定义函数 logic_cache，把一段可以复用的逻辑单独封装起来
    key_prefix: str,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    expire_seconds: int = 3600,  # 把右边计算出来的结果保存到 expire_seconds 变量中，方便后面的代码继续复用
) -> Callable[[Callable[..., Coroutine[Any, Any, T]]], Callable[..., Coroutine[Any, Any, Optional[T]]]]:  # 这一行开始一个新的代码块，下面缩进的内容都属于它
    """stale-while-revalidate 风格的热点缓存装饰器。

    适用场景：分类、配置、榜单等“读多写少且允许几秒旧值”的数据。
    """

    hard_expire_seconds = max(expire_seconds * 3, expire_seconds + 60)  # 把右边计算出来的结果保存到 hard_expire_seconds 变量中，方便后面的代码继续复用

    def decorator(  # 定义函数 decorator，把一段可以复用的逻辑单独封装起来
        func: Callable[..., Coroutine[Any, Any, T]]  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    ) -> Callable[..., Coroutine[Any, Any, Optional[T]]]:  # 这一行开始一个新的代码块，下面缩进的内容都属于它
        """接收业务函数并返回带热点缓存能力的包装函数。"""

        @wraps(func)  # 使用 wraps 装饰下面的函数或类，给它附加额外能力
        async def wrapper(*args: Any, **kwargs: Any) -> Optional[T]:  # 定义异步函数 wrapper，调用它时通常需要配合 await 使用
            """执行热点缓存读取流程，必要时触发后台刷新。"""
            cache_key = generate_cache_key(key_prefix, args, kwargs)  # 把右边计算出来的结果保存到 cache_key 变量中，方便后面的代码继续复用
            raw = await CacheUtil.get(cache_key)  # 把右边计算出来的结果保存到 raw 变量中，方便后面的代码继续复用
            now = int(time.time())  # 把右边计算出来的结果保存到 now 变量中，方便后面的代码继续复用

            if raw:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                try:  # 开始尝试执行可能出错的逻辑，如果报错就会转到下面的异常分支
                    payload = json.loads(raw)  # 把右边计算出来的结果保存到 payload 变量中，方便后面的代码继续复用
                    if payload.get("mode") == "stale":  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                        value = None if payload.get("empty", False) else payload.get("value")  # 把右边计算出来的结果保存到 value 变量中，方便后面的代码继续复用
                        expire_at = int(payload.get("expire_at", 0))  # 把右边计算出来的结果保存到 expire_at 变量中，方便后面的代码继续复用

                        if expire_at > now:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                            return value  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

                        async def refresh_task() -> None:  # 定义异步函数 refresh_task，调用它时通常需要配合 await 使用
                            """在后台刷新过期热点缓存，避免阻塞当前请求。"""
                            try:  # 开始尝试执行可能出错的逻辑，如果报错就会转到下面的异常分支
                                await singleflight.do(  # 等待这个异步操作完成，再继续执行后面的代码
                                    f"logic-refresh:{cache_key}",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                                    lambda: _refresh_logic_cache(  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                                        cache_key=cache_key,  # 把右边计算出来的结果保存到 cache_key 变量中，方便后面的代码继续复用
                                        func=func,  # 把右边计算出来的结果保存到 func 变量中，方便后面的代码继续复用
                                        args=args,  # 把右边计算出来的结果保存到 args 变量中，方便后面的代码继续复用
                                        kwargs=kwargs,  # 把右边计算出来的结果保存到 kwargs 变量中，方便后面的代码继续复用
                                        expire_seconds=expire_seconds,  # 把右边计算出来的结果保存到 expire_seconds 变量中，方便后面的代码继续复用
                                        hard_expire_seconds=hard_expire_seconds,  # 把右边计算出来的结果保存到 hard_expire_seconds 变量中，方便后面的代码继续复用
                                    ),  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
                                )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
                            except Exception:  # 如果上面 try 里的代码报错，就进入这个异常处理分支
                                logger.warning("热点缓存后台刷新失败", key=cache_key, exc_info=True)  # 记录一条日志，方便后续排查程序运行过程和定位问题

                        asyncio.create_task(refresh_task())  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                        return value  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
                except json.JSONDecodeError:  # 如果上面 try 里的代码报错，就进入这个异常处理分支
                    logger.warning("热点缓存数据损坏，按未命中处理", key=cache_key)  # 记录一条日志，方便后续排查程序运行过程和定位问题

            result = await func(*args, **kwargs)  # 把右边计算出来的结果保存到 result 变量中，方便后面的代码继续复用
            await _write_logic_cache(cache_key, result, expire_seconds, hard_expire_seconds)  # 等待这个异步操作完成，再继续执行后面的代码
            return None if _looks_like_empty(result) else result  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

        return wrapper  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    return decorator  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束


async def _write_logic_cache(  # 定义异步函数 _write_logic_cache，调用它时通常需要配合 await 使用
    cache_key: str,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    result: Any,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    expire_seconds: int,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    hard_expire_seconds: int,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
) -> None:  # 这一行开始一个新的代码块，下面缩进的内容都属于它
    """写入 stale-while-revalidate payload。"""

    payload = {  # 把右边计算出来的结果保存到 payload 变量中，方便后面的代码继续复用
        "mode": "stale",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        "version": 1,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        "expire_at": int(time.time()) + expire_seconds,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        "empty": _looks_like_empty(result),  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        "value": None if _looks_like_empty(result) else _normalize_cache_value(result),  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    }  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
    await CacheUtil.set_raw_json(cache_key, payload, ex=hard_expire_seconds)  # 等待这个异步操作完成，再继续执行后面的代码


async def _refresh_logic_cache(  # 定义异步函数 _refresh_logic_cache，调用它时通常需要配合 await 使用
    cache_key: str,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    func: Callable[..., Coroutine[Any, Any, T]],  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    args: Iterable[Any],  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    kwargs: dict[str, Any],  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    expire_seconds: int,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    hard_expire_seconds: int,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
) -> None:  # 这一行开始一个新的代码块，下面缩进的内容都属于它
    """后台刷新热点缓存。"""

    result = await func(*args, **kwargs)  # 把右边计算出来的结果保存到 result 变量中，方便后面的代码继续复用
    await _write_logic_cache(cache_key, result, expire_seconds, hard_expire_seconds)  # 等待这个异步操作完成，再继续执行后面的代码
