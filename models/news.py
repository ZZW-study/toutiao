# -*- coding: utf-8 -*-
"""新闻与分类相关的数据库模型。

本模块定义了新闻系统的核心数据模型：
- Category: 新闻分类表，存储分类字典（科技、财经、体育等）
- News: 新闻正文表，存储新闻的完整内容

数据关系：
-----------
Category (1) <-----> (N) News
- 一个分类下有多篇新闻
- 一篇新闻属于一个分类

索引设计：
-----------
- category_id 索引：加速按分类查询新闻列表
- publish_time 索引：加速按时间排序查询
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin
from utils.repr_return import generate_repr


class Category(Base):
    """新闻分类表模型。

    存储新闻分类的字典数据，如"科技"、"财经"、"体育"等。
    这是一张相对静态的表，分类数量有限且变化频率低。

    表名：news_category

    字段说明：
    ----------
    id: 分类 ID，主键自增
    name: 分类名称，唯一约束，如"科技"、"财经"
    sort_order: 排序权重，用于控制分类在前端的显示顺序

    为什么不继承 TimestampMixin？
    - 分类数据变化频率极低
    - 不需要追踪创建和更新时间
    - 减少不必要的字段
    """

    __tablename__ = "news_category"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="分类ID")
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="分类名称")
    sort_order: Mapped[int] = mapped_column(Integer, autoincrement=True, nullable=False, comment="排序")

    def __repr__(self):
        """返回便于调试的模型字符串表示。"""
        return generate_repr(self)


class News(Base, TimestampMixin):
    """新闻正文表模型。

    存储新闻的核心数据：标题、摘要、正文、作者、分类、浏览量等。
    这是新闻系统最核心的业务表，数据量大、访问频繁。

    表名：news

    字段说明：
    ----------
    id: 新闻 ID，主键自增
    title: 新闻标题，最长 255 字符
    description: 新闻摘要/简介，最长 500 字符
    content: 新闻正文，使用 Text 类型存储长文本
    image: 封面图片 URL，可选
    author: 作者名称，可选
    category_id: 分类 ID，外键关联 Category 表
    views: 浏览量，默认 0
    publish_time: 发布时间，默认为当前时间

    索引设计：
    ----------
    - fk_news_category_id: 分类 ID 索引，加速按分类查询
    - idx_publish_id: 发布时间索引，加速按时间排序

    继承说明：
    ----------
    继承 TimestampMixin 获得：
    - created_at: 记录创建时间
    - updated_at: 记录更新时间
    """

    __tablename__ = "news"

    # 索引定义：覆盖高频查询场景
    __table_args__ = (
        Index("fk_news_category_id", "category_id"),  # 按分类查询
        Index("idx_publish_id", "publish_time"),  # 按时间排序
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
        """返回便于调试的模型字符串表示。"""
        return generate_repr(self)
