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
    """用户主表模型。

    存储用户注册后的基础资料，是用户系统的核心表。

    表名：user

    字段说明：
    ----------
    id: 用户 ID，主键自增
    username: 用户名，唯一，用于登录
    password: 密码，存储 bcrypt 加密后的哈希值
    nickname: 昵称，显示名称，可选
    avatar: 头像 URL，有默认图片
    gender: 性别，枚举值 male/female/unknown
    bio: 个人简介，可选
    phone: 手机号，唯一，可选

    索引设计：
    ----------
    - username_UNIQUE: 用户名唯一索引，加速登录查询
    - phone_UNIQUE: 手机号唯一索引，防止重复绑定

    继承说明：
    ----------
    继承 TimestampMixin 获得：
    - created_at: 注册时间
    - updated_at: 资料更新时间
    """

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
    """用户登录令牌表模型。

    管理用户的登录状态，支持：
    - 多设备登录：一个用户可以有多个有效令牌
    - 令牌过期：通过 expires_at 控制有效期
    - 主动失效：服务端可以删除令牌强制下线

    表名：user_token

    字段说明：
    ----------
    id: 令牌 ID，主键自增
    user_id: 用户 ID，外键关联 User 表
    token: 令牌值，通常是随机生成的字符串
    expires_at: 过期时间，令牌在此时间后失效
    created_at: 创建时间，记录登录时间

    为什么需要令牌表？
    ------------------
    - 无状态 JWT vs 有状态令牌：
      - JWT 不需要存储，但无法主动失效
      - 数据库令牌可以主动删除，实现强制下线
    - 本项目选择数据库令牌，安全性更高
    """

    __tablename__ = "user_token"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True, comment="令牌ID")
    user_id: Mapped[int] = mapped_column(Integer, ForeignKey(User.id), nullable=False, comment="用户ID")
    token: Mapped[str] = mapped_column(String(50), nullable=False, comment="令牌值")
    expires_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, comment="过期时间")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, comment="创建时间")

    def __repr__(self):
        """返回便于调试的模型字符串表示。"""
        return generate_repr(self)
