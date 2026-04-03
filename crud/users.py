from sqlalchemy import select,update
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from models.users import User,UserToken
from schemas.users import UserRequest,UserUpdateRequest
from utils import security
from datetime import datetime, timedelta, timezone
from cache.multi_level_cache import multi_level_cache


def _now():
    """获取当前UTC时间"""
    return datetime.now(timezone.utc)


async def get_user_by_username(db: AsyncSession, username: str):
    query = select(User).where(User.username == username)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user_data: UserRequest):
    hashed_password = security.get_hash_password(user_data.password)
    user = User(username=user_data.username, password=hashed_password)
    db.add(user)
    await db.commit()
    await db.refresh(user)
    return user


async def create_token(db: AsyncSession, user_id: int):
    import uuid

    token = str(uuid.uuid4())
    expires_at = _now() + timedelta(days=7)
    query = select(UserToken).where(UserToken.user_id == user_id)
    result = await db.execute(query)
    user_token = result.scalar_one_or_none()

    if user_token:
        user_token.token = token
        user_token.expires_at = expires_at
    else:
        user_token = UserToken(user_id=user_id, token=token, expires_at=expires_at)
        db.add(user_token)
    await db.commit()
    return token


async def authenticate_user(db: AsyncSession, username: str, password: str):
    cache_key = f"user:auth:{username}"

    async def db_query():
        return await get_user_by_username(db, username)

    cached = await multi_level_cache.get(cache_key, db_query)
    if cached:
        user = cached
    else:
        user = await db_query()
        if user:
            await multi_level_cache.l2.set(cache_key, {
                "id": user.id,
                "username": user.username,
                "password": user.password
            })

    if not user:
        return "用户不存在"

    if not security.verify_password(plain_password=password, hashed_password=user.password):
        return "用户密码错误"

    return user


async def get_user_by_token(db: AsyncSession, token: str):
    query = select(UserToken).where(UserToken.token == token)
    result = await db.execute(query)
    db_token = result.scalar_one_or_none()
    if not db_token or db_token.expires_at < _now():
        return None

    query = select(User).where(User.id == db_token.user_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def update_user(db: AsyncSession, username: str, user_data: UserUpdateRequest):
    query = update(User).where(User.username == username).values(**user_data.model_dump(
        exclude_unset=True,
        exclude_none=True
    ))
    result = await db.execute(query)
    await db.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="用户不存在")

    await multi_level_cache.delete(f"user:auth:{username}")
    await multi_level_cache.delete(f"user:by_username:{username}")

    updated_user = await get_user_by_username(db, username)
    return updated_user


async def change_password(db: AsyncSession, user: User, old_password: str, new_password: str):
    if not security.verify_password(old_password, user.password):
        return False

    hashed_new_pwd = security.get_hash_password(new_password)
    user.password = hashed_new_pwd
    db.add(user)
    await db.commit()
    await db.refresh(user)

    await multi_level_cache.delete(f"user:info:{user.id}")
    await multi_level_cache.delete(f"user:auth:{user.username}")

    return True
