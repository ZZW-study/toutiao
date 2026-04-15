"""用户收藏表模型。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base
from models.news import News
from models.users import User
from utils.repr_return import generate_repr


class Favorite(Base):
    """收藏关系表。

    这张表的核心作用不是存新闻正文，而是存“谁收藏了哪篇新闻”这件事。

    设计重点：
    - 使用 `(user_id, news_id)` 唯一约束，保证同一用户不会重复收藏同一篇文章。
    - 对 `user_id`、`news_id` 建索引，便于高频查询“某用户收藏列表”或“某文章被谁收藏”。
    """

    __tablename__ = "favorite"

    __table_args__ = (
        UniqueConstraint("user_id", "news_id", name="user_news_unique"),
        Index("fk_favorite_user_idx", "user_id"),
        Index("fk_favorite_news_idx", "news_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="收藏ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey(User.id), nullable=False, comment="用户ID")
    news_id: Mapped[int] = mapped_column(Integer, ForeignKey(News.id), nullable=False, comment="新闻ID")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False, comment="创建时间")

    def __repr__(self):
        """返回便于调试的模型字符串。"""

        return generate_repr(self)
