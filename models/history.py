from sqlalchemy import Integer, DateTime, ForeignKey, Index, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, DeclarativeBase
from models.news import News
from models.users import User
from utils.repr_return import generate_repr
from datetime import datetime


"""浏览历史数据模型。

记录用户对新闻的浏览行为，每条记录包含用户、新闻及浏览时间。
包含若干索引以加速基于用户或新闻的查询操作。
"""


class Base(DeclarativeBase):
    pass


# 用户浏览历史表ORM模型
class ViewHistory(Base):
    __tablename__ = "history"

    # 索引与约束：
    # - UniqueConstraint(user_id, news_id)：保证同一用户同一篇文章只有一条历史记录，便于去重或更新时间。
    # - 为 news_id、user_id、view_time 创建索引用于高频查询（例如列出用户历史、热门文章的浏览时间分布）。
    __table_args__ = (
        UniqueConstraint('user_id', 'news_id', name='user_news_unique'),
        Index('fk_history_news_idx', 'news_id'),
        Index('idx_history_user_id', 'user_id'),
        Index('idx_history_view_time', 'view_time')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="历史ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey(User.id), nullable=False, comment="用户ID")
    news_id: Mapped[int] = mapped_column(Integer, ForeignKey(News.id), nullable=False, comment="新闻ID")
    view_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False, comment="浏览时间")

    def __repr__(self):
        return generate_repr(self)


