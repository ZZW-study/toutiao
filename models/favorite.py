# -*- coding: utf-8 -*-
"""用户收藏表模型。

本模块定义用户收藏新闻的关系表，记录"谁收藏了哪篇新闻"。

数据关系：
-----------
User (1) <-----> (N) Favorite (N) <-----> (1) News
- 一个用户可以收藏多篇新闻
- 一篇新闻可以被多个用户收藏
- Favorite 是多对多关系的中间表（但带有时间戳）

约束设计：
-----------
- (user_id, news_id) 唯一约束：防止重复收藏同一篇新闻
- user_id 索引：加速查询"用户收藏了哪些新闻"
- news_id 索引：加速查询"新闻被谁收藏了"
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base
from models.news import News
from models.users import User
from utils.repr_return import generate_repr


class Favorite(Base):
    """用户收藏关系表模型。

    记录用户收藏新闻的关系，是典型的"用户-内容"关系表。

    表名：favorite

    字段说明：
    ----------
    id: 收藏记录 ID，主键自增
    user_id: 用户 ID，外键关联 User 表
    news_id: 新闻 ID，外键关联 News 表
    created_at: 收藏时间

    约束设计：
    ----------
    - user_news_unique: (user_id, news_id) 唯一约束
      - 防止同一用户重复收藏同一篇新闻
      - 业务层需要处理"已收藏"的情况

    索引设计：
    ----------
    - fk_favorite_user_idx: user_id 索引
      - 加速查询"用户收藏列表"
      - 高频查询场景
    - fk_favorite_news_idx: news_id 索引
      - 加速查询"新闻被收藏次数"
      - 支持热门新闻统计

    为什么不继承 TimestampMixin？
    - 只需要记录收藏时间，不需要更新时间
    - 收藏记录不会被"更新"，只有新增和删除
    """

    __tablename__ = "favorite"

    __table_args__ = (
        UniqueConstraint("user_id", "news_id", name="user_news_unique"),  # 防止重复收藏
        Index("fk_favorite_user_idx", "user_id"),  # 加速查询用户收藏列表
        Index("fk_favorite_news_idx", "news_id"),  # 加速统计新闻收藏数
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="收藏ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey(User.id), nullable=False, comment="用户ID")
    news_id: Mapped[int] = mapped_column(Integer, ForeignKey(News.id), nullable=False, comment="新闻ID")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False, comment="创建时间")

    def __repr__(self):
        """返回便于调试的模型字符串表示。"""
        return generate_repr(self)
