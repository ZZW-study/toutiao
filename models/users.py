from datetime import datetime
from typing import Optional
from sqlalchemy import Index, Integer, String, Enum, DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from utils.repr_return import generate_repr


"""用户相关的数据库模型定义。

包含 `User`（用户信息）和 `UserToken`（用户登录令牌）两个表的 ORM 映射定义，
字段均带有注释（comment）方便数据库层面的说明与文档生成。
"""


# 定义ORM基类
class Base(DeclarativeBase):
    pass

# 用户信息表ORM模型
class User(Base):
    """
    用户信息表ORM模型
    """
    __tablename__ = 'user'

    # 创建唯一索引，B+树结构，相当于加个目录，通过目录查，而不是遍历整本书
    __table_args__ = (
        Index('username_UNIQUE','username', unique=True),
        Index('phone_UNIQUE','phone', unique=True),
    )

    # 字段定义
    id: Mapped[int] = mapped_column(
        Integer, 
        primary_key=True, 
        autoincrement=True, 
        comment="用户ID"
    )
    username: Mapped[str] = mapped_column(
        String(50), 
        unique=True, 
        nullable=False, 
        comment="用户名"
    )
    password: Mapped[str] = mapped_column(
        String(255), 
        nullable=False, 
        comment="密码（加密存储）"
    )
    nickname: Mapped[Optional[str]] = mapped_column(
        String(50), 
        comment="昵称"
    )
    avatar: Mapped[Optional[str]] = mapped_column(
        String(255), 
        default="https://fastly.jsdelivr.net/npm/@vant/assets/ipad-empty.png", 
        comment="头像URL"
    )
    gender: Mapped[Optional[str]] = mapped_column(
        Enum('male', 'female', 'unknown'), 
        comment="性别"
    )
    bio: Mapped[Optional[str]] = mapped_column(
        String(500), 
        default="这个人很懒，什么都没写~", 
        comment="个人简介"
    )
    phone: Mapped[Optional[str]] = mapped_column(
        String(20), 
        unique=True, 
        comment="手机号"
    )
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
    def __repr__(self):
        return generate_repr(self)

class UserToken(Base):
    __tablename__ = "user_token"

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=True,
        comment="令牌ID"
    )
    user_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey(User.id),
        nullable=False,
        comment="用户ID"
    )
    token: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        comment="令牌值"
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime,
        nullable=False,
        comment="过期时间"
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime,
        default=datetime.now,
        comment="创建时间"
    )

    def __repr__(self):
        return generate_repr(self)


