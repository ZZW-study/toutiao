# -*- coding: utf-8 -*-
"""限流配置类和数据结构定义。

包含限流维度枚举、配置类和结果返回结构。
"""


from dataclasses import dataclass
from enum import Enum

from configs.settings import get_settings


settings = get_settings()


class RateLimitDimension(Enum):
    """限流维度枚举"""
    IP = "ip"
    USER_ID = "user_id"
    COMBINED = "combined"


@dataclass
class RateLimitConfig:
    """限流配置"""
    capacity: int = settings.TOKEN_BUCKET_CAPACITY  # 桶容量（支持突发流量）
    rate: float = settings.TOKEN_RATE  # 令牌生成速率（个/秒）
    dimension: RateLimitDimension = RateLimitDimension(settings.RATE_LIMIT_DIMENSION)


@dataclass
class RateLimitResult:
    """限流结果返回结构"""
    allowed: bool  # 是否允许通过
    retry_after: float = 0.0  # 重试等待时间（秒）
    remaining_tokens: float = 0.0  # 剩余令牌数
    reason: str = ""  # 限流原因
