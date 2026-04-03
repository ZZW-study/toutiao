from datetime import datetime
from sqlalchemy import UniqueConstraint,Index,Integer,ForeignKey,DateTime
from sqlalchemy.orm import DeclarativeBase,Mapped,mapped_column
from models.news import News
from models.users import User
from utils.repr_return import generate_repr

class Base(DeclarativeBase):
    pass

class Favorite(Base):
    """
    收藏表ORM模型
    """
    __tablename__ = "favorite"

    # 创建索引
    # UniqueConstraint: 唯一约束，当前用户，当前新闻，只能收藏一次，数据库约束能 100% 阻止重复插入；
    __table_args__ = (
        UniqueConstraint('user_id',"news_id",name='user_news_unique'),
        Index('fk_favorite_user_idx','user_id'),
        Index('fk_favorite_news_idx','news_id')
    )

    id: Mapped[int] = mapped_column(Integer,primary_key=True,autoincrement=True,comment="收藏ID")
    user_id: Mapped[int] = mapped_column(Integer,ForeignKey(User.id),nullable=False,comment="用户ID")
    news_id: Mapped[int] = mapped_column(Integer,ForeignKey(News.id),nullable=False,comment="新闻ID")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False, comment="创建时间")

    def __repr__(self):
        return generate_repr(self)















