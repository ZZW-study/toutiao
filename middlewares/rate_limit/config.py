# -*- coding: utf-8 -*-
"""限流配置与数据结构定义。"""

from __future__ import annotations  # 开启延迟解析类型注解，避免前向引用在导入阶段就被过早求值

from dataclasses import dataclass  # 从 dataclasses 模块导入当前文件后续要用到的对象
from enum import Enum  # 从 enum 模块导入当前文件后续要用到的对象

from configs.settings import get_settings  # 从 configs.settings 模块导入当前文件后续要用到的对象

settings = get_settings()  # 把右边计算出来的结果保存到 settings 变量中，方便后面的代码继续复用


class RateLimitDimension(Enum):  # 定义 RateLimitDimension 类，用来把这一块相关的状态和行为组织在一起
    """限流维度枚举。"""

    IP = "ip"  # 把这个常量值保存到 IP 中，后面会作为固定配置反复使用
    USER_ID = "user_id"  # 把这个常量值保存到 USER_ID 中，后面会作为固定配置反复使用
    COMBINED = "combined"  # 把这个常量值保存到 COMBINED 中，后面会作为固定配置反复使用


@dataclass(slots=True)  # 使用 dataclass 装饰下面的函数或类，给它附加额外能力
class RateLimitConfig:  # 定义 RateLimitConfig 类，用来把这一块相关的状态和行为组织在一起
    """限流参数。"""

    capacity: int = settings.TOKEN_BUCKET_CAPACITY  # 把右边计算出来的结果保存到 capacity 变量中，方便后面的代码继续复用
    rate: float = settings.TOKEN_RATE  # 把右边计算出来的结果保存到 rate 变量中，方便后面的代码继续复用
    dimension: RateLimitDimension = RateLimitDimension(settings.RATE_LIMIT_DIMENSION)  # 把右边计算出来的结果保存到 dimension 变量中，方便后面的代码继续复用


@dataclass(slots=True)  # 使用 dataclass 装饰下面的函数或类，给它附加额外能力
class RateLimitIdentity:  # 定义 RateLimitIdentity 类，用来把这一块相关的状态和行为组织在一起
    """当前请求的限流身份。

    `key` 是真正参与 Redis 计数与本地限流的唯一标识。
    """

    key: str  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    ip: str  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    user_id: int | None  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    scope: str  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行


@dataclass(slots=True)  # 使用 dataclass 装饰下面的函数或类，给它附加额外能力
class RateLimitResult:  # 定义 RateLimitResult 类，用来把这一块相关的状态和行为组织在一起
    """限流结果。"""

    allowed: bool  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    retry_after: float = 0.0  # 把右边计算出来的结果保存到 retry_after 变量中，方便后面的代码继续复用
    remaining_tokens: float = 0.0  # 把右边计算出来的结果保存到 remaining_tokens 变量中，方便后面的代码继续复用
    reason: str = ""  # 把右边计算出来的结果保存到 reason 变量中，方便后面的代码继续复用

