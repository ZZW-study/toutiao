"""SQLAlchemy 模型公共基类。

这个文件定义了两个最基础的能力：
1. `Base`：所有 ORM 模型的共同父类。
2. `TimestampMixin`：给需要记录创建时间、更新时间的表复用时间字段。

把公共能力抽到这里，可以避免每个模型都重复写相同字段。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """项目统一的 ORM 基类。

    所有数据表模型都应该继承它，这样 SQLAlchemy 才能把它们收集到同一份元数据里，
    后续建表、删表、迁移时才知道项目一共有哪些表。
    """

    pass


class TimestampMixin:
    """时间戳混入类。

    “Mixin” 可以理解成“可插拔的公共字段包”。
    哪个模型想要 `created_at` 和 `updated_at`，
    只要继承这个类就能直接获得，不需要重复定义。
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        comment="更新时间",
    )
