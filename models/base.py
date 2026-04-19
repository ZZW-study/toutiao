# -*- coding: utf-8 -*-
"""SQLAlchemy ORM 模型公共基类。

本模块定义了所有数据库模型的共同基础类和可复用的混入类。

核心概念：
-----------
1. Base（声明式基类）
   - 所有 ORM 模型的父类
   - SQLAlchemy 通过它收集所有模型的元数据（表名、字段、索引等）
   - 继承 DeclarativeBase 是 SQLAlchemy 2.0 的推荐写法

2. TimestampMixin（时间戳混入类）
   - 提供 created_at 和 updated_at 字段
   - 模型通过多重继承获得这两个字段
   - 避免在每个模型中重复定义相同字段

设计模式：
-----------
- 基类继承：所有模型继承 Base，获得 ORM 能力
- 混入类：通过多重继承复用字段定义，比继承更灵活

使用示例：
-----------
class User(Base, TimestampMixin):
    __tablename__ = "user"
    id: Mapped[int] = mapped_column(primary_key=True)
    # 自动拥有 created_at 和 updated_at 字段
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    """项目统一的 ORM 声明式基类。

    所有数据表模型都必须继承这个类，原因：
    - SQLAlchemy 需要知道哪些类是 ORM 模型
    - Base 提供了元数据收集、会话绑定等核心能力
    - 继承 DeclarativeBase 是 SQLAlchemy 2.0 的标准写法

    为什么这个类是空的？
    - 它只提供基础设施，不需要额外字段
    - 所有表级别的配置在子类中定义
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
