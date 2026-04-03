from sqlalchemy import Integer,DateTime,ForeignKey,Index,UniqueConstraint
from sqlalchemy.orm import Mapped,mapped_column,DeclarativeBase
from models.news import News
from models.users import User
from utils.repr_return import generate_repr
from datetime import datetime

class Base(DeclarativeBase):
    pass


# 用户浏览历史表ORM模型
class ViewHistory(Base):
    __tablename__ = "history"

    # 有查询需求，使用where,用索引
    __table_args__ = (
        UniqueConstraint('user_id','news_id',name='user_news_unique'),
        Index('fk_history_news_idx','news_id'),
        Index('idx_history_user_id','user_id'),
        Index('idx_history_view_time','view_time')
    )

    id: Mapped[int] = mapped_column(Integer,primary_key=True,autoincrement=True,comment="历史ID")
    user_id: Mapped[int] = mapped_column(Integer,ForeignKey(User.id),nullable=False,comment="用户ID")
    news_id: Mapped[int] = mapped_column(Integer,ForeignKey(News.id),nullable=False,comment="新闻ID")
    view_time: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, nullable=False, comment="浏览时间")

    def __repr__(self):
        return generate_repr(self)


