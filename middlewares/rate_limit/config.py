# -*- coding: utf-8 -*-
"""限流配置与数据结构定义。"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum

from configs.settings import get_settings

settings = get_settings()


class RateLimitDimension(Enum):
    """限流维度枚举。"""

    IP = "ip"
    USER_ID = "user_id"
    COMBINED = "combined"


@dataclass(slots=True)
class RateLimitConfig:
    """限流参数。"""

    capacity: int = settings.TOKEN_BUCKET_CAPACITY
    rate: float = settings.TOKEN_RATE
    dimension: RateLimitDimension = RateLimitDimension(settings.RATE_LIMIT_DIMENSION)


@dataclass(slots=True)
class RateLimitIdentity:
    """当前请求的限流身份。

    `key` 是真正参与 Redis 计数与本地限流的唯一标识。
    """

    key: str
    ip: str
    user_id: int | None
    scope: str


@dataclass(slots=True)
class RateLimitResult:
    """限流结果。"""

    allowed: bool
    retry_after: float = 0.0
    remaining_tokens: float = 0.0
    reason: str = ""

