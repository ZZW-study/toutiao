# -*- coding: utf-8 -*-
"""浏览历史表模型。

本模块定义用户浏览新闻的历史记录表，记录"用户看过什么新闻、什么时候看的"。

数据关系：
-----------
User (1) <-----> (N) ViewHistory (N) <-----> (1) News
- 一个用户可以浏览多篇新闻
- 一篇新闻可以被多个用户浏览
- ViewHistory 记录每次浏览的时间和用户

约束设计：
-----------
- (user_id, news_id) 唯一约束：同一用户对同一新闻只保留一条记录
- 再次浏览时更新 view_time，而不是新增记录

业务用途：
-----------
- 个性化推荐：基于浏览历史推荐相关新闻
- 用户行为分析：统计用户兴趣偏好
- 浏览记录展示：在"历史"页面展示用户看过的新闻
"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base
from models.news import News
from models.users import User
from utils.repr_return import generate_repr


class ViewHistory(Base):
    """用户浏览历史表模型。

    记录用户浏览新闻的历史，支持：
    - 浏览记录展示
    - 个性化推荐
    - 用户行为分析

    表名：history

    字段说明：
    ----------
    id: 历史记录 ID，主键自增
    user_id: 用户 ID，外键关联 User 表
    news_id: 新闻 ID，外键关联 News 表
    view_time: 浏览时间，记录最近一次浏览的时间

    约束设计：
    ----------
    - user_news_unique: (user_id, news_id) 唯一约束
      - 同一用户对同一新闻只保留一条记录
      - 再次浏览时更新 view_time（业务层处理）

    索引设计：
    ----------
    - fk_history_news_idx: news_id 索引
      - 加速查询"新闻被多少人看过"
      - 支持热度统计
    - idx_history_user_id: user_id 索引
      - 加速查询"用户浏览历史列表"
      - 高频查询场景
    - idx_history_view_time: view_time 索引
      - 加速按时间排序查询
      - 支持"最近浏览"功能

    为什么不继承 TimestampMixin？
    - 只需要记录浏览时间，不需要创建/更新时间
    - view_time 会在再次浏览时更新
    """

    __tablename__ = "history"

    __table_args__ = (
        UniqueConstraint("user_id", "news_id", name="user_news_unique"),  # 防止重复记录
        Index("fk_history_news_idx", "news_id"),  # 加速统计新闻浏览量
        Index("idx_history_user_id", "user_id"),  # 加速查询用户历史
        Index("idx_history_view_time", "view_time"),  # 加速按时间排序
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="历史ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey(User.id), nullable=False, comment="用户ID")
    news_id: Mapped[int] = mapped_column(Integer, ForeignKey(News.id), nullable=False, comment="新闻ID")
    view_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False, comment="浏览时间")

    def __repr__(self):
        """返回便于调试的模型字符串表示。"""
        return generate_repr(self)
