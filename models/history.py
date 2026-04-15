"""浏览历史表模型。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base
from models.news import News
from models.users import User
from utils.repr_return import generate_repr


class ViewHistory(Base):
    """用户浏览历史表。

    这张表记录的是“用户看过什么新闻、什么时候看的”。

    这里使用唯一约束 `(user_id, news_id)` 的原因是：
    - 可以避免同一篇新闻被重复插入多条历史记录。
    - 如果业务想表达“再次浏览”，更适合更新 `view_time`，而不是无限新增重复行。
    """

    __tablename__ = "history"

    __table_args__ = (
        UniqueConstraint("user_id", "news_id", name="user_news_unique"),
        Index("fk_history_news_idx", "news_id"),
        Index("idx_history_user_id", "user_id"),
        Index("idx_history_view_time", "view_time"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="历史ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey(User.id), nullable=False, comment="用户ID")
    news_id: Mapped[int] = mapped_column(Integer, ForeignKey(News.id), nullable=False, comment="新闻ID")
    view_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False, comment="浏览时间")

    def __repr__(self):
        """返回便于调试的模型字符串。"""

        return generate_repr(self)
