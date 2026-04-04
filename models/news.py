from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from datetime import datetime
from sqlalchemy import DateTime, ForeignKey, Integer, String, Text, Index
from typing import Optional
from utils.repr_return import generate_repr


"""数据库模型定义：新闻（News）与分类（Category）。

本文件定义 ORM 映射类，分别对应底层数据库中的 `news` 和
`news_category` 表。使用 SQLAlchemy 2.0 风格的 DeclarativeBase，
并在字段上使用 `mapped_column` 指定列类型、约束与注释（comment），
便于自动建表与文档生成。
"""


# 先看新闻数据库，有没有公共的列表:有 -->创建时间，更新时间 -->封装为基础模型类
class Base(DeclarativeBase):
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        comment="创建时间"
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        onupdate=datetime.now,
        comment="更新时间"
    )


# 新闻类别类 --- 它与数据库中的某一张实际数据表.
# 建立了映射关系。通过操作Category类，即可间接操作对应的底层数据表，无需直接编写原生 SQL。
class Category(Base):  
    __tablename__ = "news_category"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="分类ID"
    )
    name: Mapped[str] = mapped_column(
        String(50),
        unique=True,
        nullable=False,
        comment="分类名称"
    )
    sort_order: Mapped[int] = mapped_column(
        Integer,
        autoincrement=True,
        nullable=False,
        comment="排序"
    )

    def __repr__(self): #魔法方法，返回一个能 “准确描述该类实例对象” 的字符串，方便开发者调试和查看对象的核心属性信息
        return generate_repr(self)

# 新闻表类
class News(Base):
    __tablename__ = "news"

    #创建索引，提升查询速度,Index('索引名', '字段名') 表示为指定字段创建索引：
    __table_args__ = (
        Index('fk_news_category_id','category_id'),
        Index('idx_publish_id','publish_time')
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="新闻ID"
    )

    title: Mapped[str] = mapped_column(
        String(255),
        nullable = False,
        comment="新闻标题"
    )

    description: Mapped[Optional[str]] = mapped_column(
        String(500),
        nullable=False,
        comment="新闻简介"
    )

    content: Mapped[str] = mapped_column(
        Text,
        nullable=False,
        comment="新闻内容"
    )

    image: Mapped[Optional[str]] = mapped_column(
        String(255),
        nullable=True,
        comment="封面图片URL"
    )

    author: Mapped[Optional[str]] = mapped_column(
        String(50),
        comment="作者"
    )

    category_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(Category.id),
        nullable=False,
        comment="分类ID"
    )

    views: Mapped[int] = mapped_column(
        Integer,
        default=0,
        nullable=False,
        comment="浏览量"
    )

    publish_time: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        comment="发布时间"
    )

    def __repr__(self):
        return generate_repr(self)




