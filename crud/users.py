"""用户相关 CRUD 与认证逻辑。"""

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

# 路由层依赖这两个常量来决定返回语义，因此保留稳定文案。
USER_NOT_FOUND = "用户不存在"
INVALID_PASSWORD = "用户密码错误"


def _now() -> datetime:
    """返回 naive UTC 时间。

    当前表结构中的 `expires_at` 也是普通 `DateTime` 字段，
    统一使用 naive UTC 可以避免 sqlite/mysql 下出现 aware 与 naive 混比较问题。
    """

    return datetime.utcnow()


async def get_user_by_username(db: AsyncSession, username: str) -> User | None:
    """按用户名查询用户。"""

    result = await db.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user_data: UserRequest) -> User:
    """创建用户并保存哈希密码。"""

    hashed_password = security.get_hash_password(user_data.password)
    user = User(username=user_data.username, password=hashed_password)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def create_token(db: AsyncSession, user_id: int) -> str:
    """创建或刷新登录 token。

    项目当前仍然使用数据库保存的随机 token，因此这里统一做“单用户单 token”刷新。
    """

    token = str(uuid.uuid4())
    expires_at = _now() + timedelta(days=7)

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


async def authenticate_user(
    db: AsyncSession,
    username: str,
    password: str,
) -> User | str:
    """校验用户名和密码。

    这里移除了对 ORM 对象的缓存。
    认证链路最重要的是正确性，直接查询数据库比缓存一个 `User ORM` 更稳妥。
    """

    user = await get_user_by_username(db, username)
    if user is None:
        return USER_NOT_FOUND

    if not security.verify_password(plain_password=password, hashed_password=user.password):
        return INVALID_PASSWORD

    return user


async def get_user_id_by_token(db: AsyncSession, token: str) -> int | None:
    """根据 token 解析用户 ID。

    这个轻量查询专门给限流和认证上下文复用，避免无意义地把整张用户记录都查出来。
    """

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
    """根据 token 获取当前登录用户。"""

    stmt = (
        select(User)
        .join(UserToken, UserToken.user_id == User.id)
        .where(UserToken.token == token, UserToken.expires_at >= _now())
    )
    result = await db.execute(stmt)
    return result.scalar_one_or_none()


async def update_user(
    db: AsyncSession,
    username: str,
    user_data: UserUpdateRequest,
) -> User:
    """更新用户资料。"""

    result = await db.execute(
        update(User)
        .where(User.username == username)
        .values(**user_data.model_dump(exclude_unset=True, exclude_none=True))
    )
    await db.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail=USER_NOT_FOUND)

    # 这里保留缓存失效逻辑，确保后续如果重新接入用户信息缓存不会读到旧值。
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
    """修改密码。"""

    if not security.verify_password(old_password, user.password):
        return False

    user.password = security.get_hash_password(new_password)
    db.add(user)
    await db.commit()
    await db.refresh(user)

    await multi_level_cache.delete(f"user:info:{user.id}")
    await multi_level_cache.delete(f"user:auth:{user.username}")
    return True

