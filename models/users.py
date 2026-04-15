"""用户与登录令牌相关的数据库模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin
from utils.repr_return import generate_repr


class User(Base, TimestampMixin):
    """用户主表。

    这张表保存用户注册后的基础资料，例如用户名、密码哈希、头像、手机号等。
    """

    __tablename__ = "user"

    __table_args__ = (
        Index("username_UNIQUE", "username", unique=True),
        Index("phone_UNIQUE", "phone", unique=True),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="用户ID")
    username: Mapped[str] = mapped_column(String(50), unique=True, nullable=False, comment="用户名")
    password: Mapped[str] = mapped_column(String(255), nullable=False, comment="密码（加密存储）")
    nickname: Mapped[Optional[str]] = mapped_column(String(50), comment="昵称")
    avatar: Mapped[Optional[str]] = mapped_column(
        String(255),
        default="https://fastly.jsdelivr.net/npm/@vant/assets/ipad-empty.png",
        comment="头像URL",
    )
    gender: Mapped[Optional[str]] = mapped_column(Enum("male", "female", "unknown"), comment="性别")
    bio: Mapped[Optional[str]] = mapped_column(String(500), default="这个人很懒，什么都没写~", comment="个人简介")
    phone: Mapped[Optional[str]] = mapped_column(String(20), unique=True, comment="手机号")

    def __repr__(self):
        """返回便于调试的模型字符串。"""

        return generate_repr(self)


class UserToken(Base):
    """用户登录令牌表。

    当前项目没有直接上 JWT，而是把令牌持久化到数据库中，
    这样服务端可以明确知道某个 token 是否存在、是否过期。
    """

    __tablename__ = "user_token"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="令牌ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey(User.id), nullable=False, comment="用户ID")
    token: Mapped[str] = mapped_column(String(50), nullable=False, comment="令牌值")
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="过期时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")

    def __repr__(self):
        """返回便于调试的模型字符串。"""

        return generate_repr(self)
