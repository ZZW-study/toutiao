"""新闻与分类相关的数据库模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin
from utils.repr_return import generate_repr


class Category(Base):
    """新闻分类表。

    这张表的作用很简单，就是维护分类字典，例如“科技”“财经”“体育”。
    因为它本身变化很少，所以没有继承时间戳混入类。
    """

    __tablename__ = "news_category"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="分类ID")
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="分类名称")
    sort_order: Mapped[int] = mapped_column(Integer, autoincrement=True, nullable=False, comment="排序")

    def __repr__(self):
        """返回便于调试的模型字符串。"""

        return generate_repr(self)


class News(Base, TimestampMixin):
    """新闻正文表。

    这张表保存的是新闻主数据，包含标题、摘要、正文、作者、分类、浏览量等字段。
    它是整个项目最核心的数据表之一。
    """

    __tablename__ = "news"

    __table_args__ = (
        Index("fk_news_category_id", "category_id"),
        Index("idx_publish_id", "publish_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="新闻ID")
    title: Mapped[str] = mapped_column(String(255), nullable=False, comment="新闻标题")
    description: Mapped[Optional[str]] = mapped_column(String(500), nullable=False, comment="新闻简介")
    content: Mapped[str] = mapped_column(Text, nullable=False, comment="新闻内容")
    image: Mapped[Optional[str]] = mapped_column(String(255), nullable=True, comment="封面图片URL")
    author: Mapped[Optional[str]] = mapped_column(String(50), comment="作者")
    category_id: Mapped[int] = mapped_column(Integer, ForeignKey(Category.id), nullable=False, comment="分类ID")
    views: Mapped[int] = mapped_column(Integer, default=0, nullable=False, comment="浏览量")
    publish_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="发布时间")

    def __repr__(self):
        """返回便于调试的模型字符串。"""

        return generate_repr(self)
