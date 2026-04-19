# -*- coding: utf-8 -*-
"""用户相关 CRUD 与认证逻辑。

提供用户的增删改查、登录认证、Token 管理等功能。
"""

from __future__ import annotations

import uuid
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from cache.multi_level_cache import multi_level_cache
from models.users import User, UserToken
from schemas.users import UserRequest, UserUpdateRequest
from utils import security

# 错误提示常量
USER_NOT_FOUND = "用户不存在"
INVALID_PASSWORD = "用户密码错误"


def _now() -> datetime:
    """返回 naive UTC 时间，避免时区问题。"""
    return datetime.utcnow()


# ---- 用户查询与创建 ----

async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    """按用户名查询用户。"""
    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user_data: UserRequest) -> User:
    """创建用户，密码加密后存储。"""
    hashed_password = security.get_hash_password(user_data.password)
    user = User(username=user_data.username, password=hashed_password)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


# ---- Token 管理 ----

async def create_token(db: AsyncSession, user_id: int) -> str:
    """创建登录 Token，单用户单 Token 策略。"""
    token = str(uuid.uuid4())
    expires_at = _now() + timedelta(days=7)

    # 查找是否已有 Token，有则刷新
    result = await db.execute(select(UserToken).where(UserToken.user_id == user_id))
    user_token = result.scalar_one_or_none()

    if user_token is None:
        user_token = UserToken(user_id=user_id, token=token, expires_at=expires_at)
        db.add(user_token)
    else:
        user_token.token = token
        user_token.expires_at = expires_at

    await db.commit()
    return token


# ---- 认证与鉴权 ----

async def authenticate_user(
    db: AsyncSession,
    username: str,
    password: str,
) -> User | str:
    """校验用户名和密码，成功返回 User，失败返回错误信息。"""
    user = await get_user_by_username(db, username)
    if user is None:
        return USER_NOT_FOUND

    if not security.verify_password(plain_password=password, hashed_password=user.password):
        return INVALID_PASSWORD

    return user


async def get_user_id_by_token(db: AsyncSession, token: str) -> int | None:
    """根据 Token 解析用户 ID，用于限流和认证上下文。"""
    result = await db.execute(
        select(UserToken.user_id, UserToken.expires_at).where(UserToken.token == token)
    )
    row = result.first()
    if row is None:
        return None
    user_id, expires_at = row
    if expires_at < _now():
        return None
    return user_id


async def get_user_by_token(db: AsyncSession, token: str) -> User | None:
    """根据 Token 获取当前登录用户。"""
    stmt = (
        select(User)
        .join(UserToken, UserToken.user_id == User.id)
        .where(UserToken.token == token, UserToken.expires_at >= _now())
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


# ---- 用户资料更新 ----

async def update_user(
    db: AsyncSession,
    username: str,
    user_data: UserUpdateRequest,
) -> User:
    """更新用户资料，更新后失效相关缓存。"""
    result = await db.execute(
        update(User)
        .where(User.username == username)
        .values(**user_data.model_dump(exclude_unset=True, exclude_none=True))
    )
    await db.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND)

    # 失效相关缓存
    await multi_level_cache.delete(f"user:auth:{username}")
    await multi_level_cache.delete(f"user:by_username:{username}")

    updated_user = await get_user_by_username(db, username)
    if updated_user is None:
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND)
    return updated_user


async def change_password(
    db: AsyncSession,
    user: User,
    old_password: str,
    new_password: str,
) -> bool:
    """修改密码，成功后失效用户缓存。"""
    if not security.verify_password(old_password, user.password):
        return False

    user.password = security.get_hash_password(new_password)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    await multi_level_cache.delete(f"user:info:{user.id}")
    await multi_level_cache.delete(f"user:auth:{user.username}")
    return True
