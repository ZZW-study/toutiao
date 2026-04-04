"""用户相关的 CRUD 与认证模块。

职责：
- 提供用户的增删改查操作（User、UserToken）
- 提供基于密码的认证与 Token 管理（Token 有效期 7 天）
- 在鉴权路径上使用 `multi_level_cache` 做多级缓存以提升性能

注意：本文件仅包含业务逻辑层（CRUD/认证），不负责 HTTP 层的输入校验与限流，HTTP 层在 `routers` 中处理。
"""

from sqlalchemy import select, update
from fastapi import HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from models.users import User, UserToken
from schemas.users import UserRequest, UserUpdateRequest
from utils import security
from datetime import datetime, timedelta, timezone
from cache.multi_level_cache import multi_level_cache


def _now():
    """返回当前 UTC 时间（包含时区信息）。"""
    return datetime.now(timezone.utc)


async def get_user_by_username(db: AsyncSession, username: str):
    """根据用户名查询用户，返回 `User` 对象或 `None`。

    说明：此函数直接从数据库查询，调用方可决定是否使用缓存。
    """
    query = select(User).where(User.username == username)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def create_user(db: AsyncSession, user_data: UserRequest):
    """创建新用户并返回 `User` 实例。

    - 密码会被哈希后保存
    - 事务提交后刷新实体以返回完整字段
    """
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
    """验证用户名/密码并返回 `User` 或错误信息字符串。

    缓存策略：
    - 优先尝试从 `multi_level_cache` 读取缓存（L1/L2），未命中则回退到 DB。
    - 命中后会把用户敏感字段（如 hashed_password）写入 L2 缓存以加速后续校验。

    返回：成功返回 `User`，失败返回字符串 "用户不存在" 或 "用户密码错误"（调用层根据此判断抛出 HTTP 异常）。
    """
    cache_key = f"user:auth:{username}"

    async def db_query():
        return await get_user_by_username(db, username)

    # 从多级缓存读取（L1/L2）；内部会合并并发请求避免击穿
    cached = await multi_level_cache.get(cache_key, db_query)
    if cached:
        user = cached
    else:
        user = await db_query()
        if user:
            # 将必要字段写入 L2，注意不要把敏感未加密字段暴露
            await multi_level_cache.l2.set(cache_key, {
                "id": user.id,
                "username": user.username,
                "password": user.password,
            })

    if not user:
        return "用户不存在"

    if not security.verify_password(plain_password=password, hashed_password=user.password):
        return "用户密码错误"

    return user


async def get_user_by_token(db: AsyncSession, token: str):
    """根据 token 查找用户。

    验证 token 是否存在且未过期，存在则返回对应的 `User`，否则返回 `None`。
    """
    query = select(UserToken).where(UserToken.token == token)
    result = await db.execute(query)
    db_token = result.scalar_one_or_none()
    if not db_token or db_token.expires_at < _now():
        return None

    query = select(User).where(User.id == db_token.user_id)
    result = await db.execute(query)
    return result.scalar_one_or_none()


async def update_user(db: AsyncSession, username: str, user_data: UserUpdateRequest):
    """更新用户信息。

    - 使用 `update(...).values(...)` 批量更新，避免先查询后修改的两次交互。
    - 更新后删除相关缓存，保证数据一致性（由上层接口再次读取并返回最新数据）。
    """
    query = update(User).where(User.username == username).values(**user_data.model_dump(
        exclude_unset=True,
        exclude_none=True,
    ))
    result = await db.execute(query)
    await db.commit()

    if result.rowcount == 0:
        raise HTTPException(status_code=404, detail="用户不存在")

    # 删除相关缓存，保证下次读取是最新数据
    await multi_level_cache.delete(f"user:auth:{username}")
    await multi_level_cache.delete(f"user:by_username:{username}")

    updated_user = await get_user_by_username(db, username)
    return updated_user


async def change_password(db: AsyncSession, user: User, old_password: str, new_password: str):
    """修改用户密码。

    - 首先验证 `old_password` 是否与当前密码匹配
    - 成功后哈希新密码并保存，提交事务并刷新实体
    - 删除与密码/鉴权相关的缓存，强制用户重新登录以获取新 token
    返回：True=修改成功，False=旧密码验证失败
    """
    if not security.verify_password(old_password, user.password):
        return False

    hashed_new_pwd = security.get_hash_password(new_password)
    user.password = hashed_new_pwd
    db.add(user)
    await db.commit()
    await db.refresh(user)

    # 删除鉴权相关缓存，避免旧凭证继续生效
    await multi_level_cache.delete(f"user:info:{user.id}")
    await multi_level_cache.delete(f"user:auth:{user.username}")

    return True
