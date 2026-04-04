from datetime import datetime
from sqlalchemy import UniqueConstraint, Index, Integer, ForeignKey, DateTime
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from models.news import News
from models.users import User
from utils.repr_return import generate_repr


"""用户收藏（Favorite）数据模型。

记录用户对文章的收藏行为。通过唯一约束与索引提升插入安全性与查询性能。
"""


class Base(DeclarativeBase):
    pass


class Favorite(Base):
    """收藏表 ORM 模型。

    说明：
    - 通过 UniqueConstraint(user_id, news_id) 保证同一用户对同一文章只能收藏一次，
      这是数据库级别的强一致性保证，优于仅在应用层去重。
    - 为 user_id、news_id 创建索引，提高按用户或按文章查询收藏记录的速度。
    """
    __tablename__ = "favorite"

    __table_args__ = (
        UniqueConstraint('user_id', "news_id", name='user_news_unique'),
        Index('fk_favorite_user_idx', 'user_id'),
        Index('fk_favorite_news_idx', 'news_id')
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="收藏ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey(User.id), nullable=False, comment="用户ID")
    news_id: Mapped[int] = mapped_column(Integer, ForeignKey(News.id), nullable=False, comment="新闻ID")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False, comment="创建时间")

    def __repr__(self):
        return generate_repr(self)















