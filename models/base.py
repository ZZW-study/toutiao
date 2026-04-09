from datetime import datetime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime


"""统一的 ORM 基类定义。

本文件提供 SQLAlchemy 2.0 风格的 DeclarativeBase 基类，
所有数据库模型都应继承此基类以确保元数据统一管理。
"""


# 统一的 ORM 基类
# 所有数据库模型都应继承此类，确保 SQLAlchemy 元数据统一管理
class Base(DeclarativeBase):
    """统一的 ORM 基类。

    所有数据库模型都应继承此类。
    使用 SQLAlchemy 2.0 的 DeclarativeBase 风格。
    """
    pass


# 时间戳混入类
# 提供统一的 created_at 和 updated_at 字段，需要时间戳的模型可继承此类
class TimestampMixin:
    """时间戳混入类。

    为模型提供统一的创建时间和更新时间字段。
    - created_at: 记录创建时间，默认为当前时间
    - updated_at: 记录更新时间，创建时默认为当前时间，每次更新时自动更新

    使用方式：
        class MyModel(Base, TimestampMixin):
            __tablename__ = "my_table"
            # ... 其他字段
    """
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        comment="更新时间"
    )
