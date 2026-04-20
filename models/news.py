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


class Category(Base,TimestampMixin):
    """新闻分类表模型。"""

    __tablename__ = "news_category"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="分类ID")
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="分类名称")
    sort_order: Mapped[int] = mapped_column(Integer, autoincrement=True, nullable=False, comment="排序")

    def __repr__(self):
        """返回便于调试的模型字符串表示。"""
        return generate_repr(self)


class News(Base, TimestampMixin):
    """新闻正文表模型。"""

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
