# -*- coding: utf-8 -*-
"""SQLAlchemy ORM 模型公共基类。
本模块定义了所有数据库模型的共同基础类和可复用的混入类。
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """项目统一的 ORM 声明式基类。
    """

    pass


class TimestampMixin:
    """时间戳混入类，提供创建时间和更新时间字段。

    混入类（Mixin）是一种复用代码的方式：
    - 不作为独立类使用，而是被其他类"混入"
    - 通过多重继承获得混入类的字段和方法
    - 比单继承更灵活，可以组合多个混入类

    字段说明：
    ----------
    created_at: 创建时间
        - 新记录插入时自动设置为当前时间
        - 之后不再变化

    updated_at: 更新时间
        - 新记录插入时设置为当前时间
        - 每次更新记录时自动刷新为当前时间
        - 通过 onupdate=datetime.now 实现

    使用示例：
    ----------
    class News(Base, TimestampMixin):
        __tablename__ = "news"
        id: Mapped[int] = mapped_column(primary_key=True)
        title: Mapped[str] = mapped_column(String(255))
        # 自动拥有 created_at 和 updated_at
    """

    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,  # 插入时设置为当前时间
        comment="创建时间",
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,  # 插入时设置为当前时间
        onupdate=datetime.now,  # 更新时自动刷新为当前时间
        comment="更新时间",
    )
