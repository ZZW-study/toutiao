# -*- coding: utf-8 -*-
"""用户与登录令牌相关的数据库模型。

本模块定义了用户系统的核心数据模型：
- User: 用户主表，存储用户基础资料
- UserToken: 登录令牌表，管理用户登录状态

数据关系：
-----------
User (1) <-----> (N) UserToken
- 一个用户可以有多个登录令牌（多设备登录）
- 每个令牌关联一个用户

安全设计：
-----------
- 密码存储：使用 bcrypt 加密，不明文存储
- 令牌管理：令牌持久化到数据库，支持服务端主动失效
- 唯一约束：用户名和手机号唯一，防止重复注册
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Enum, ForeignKey, Index, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from models.base import Base, TimestampMixin
from utils.repr_return import generate_repr


class User(Base, TimestampMixin):
    """用户主表模型。"""

    __tablename__ = "user"

    # 唯一索引：防止用户名和手机号重复
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
        """返回便于调试的模型字符串表示。"""
        return generate_repr(self)


class UserToken(Base):
    """用户登录令牌表模型。"""

    __tablename__ = "user_token"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="令牌ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey(User.id), nullable=False, comment="用户ID")
    token: Mapped[str] = mapped_column(String(50), nullable=False, comment="令牌值")
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="过期时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")

    def __repr__(self):
        """返回便于调试的模型字符串表示。"""
        return generate_repr(self)
