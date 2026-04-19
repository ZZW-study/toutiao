# -*- coding: utf-8 -*-
"""认证与请求身份解析工具。"""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from configs.db import get_db
from crud import users
from models.users import User


def extract_bearer_token(authorization: str | None) -> str | None:
    """从 Authorization 头中提取 token，兼容 `Bearer xxx` 和直接传 `xxx`。"""
    if not authorization:
        return None

    parts = authorization.split()
    if len(parts) == 2 and parts[0].lower() == "bearer":
        return parts[1]
    return authorization


async def resolve_request_user_id(
    request: Request,
    db: AsyncSession,
    authorization: str | None = None,
) -> int | None:
    """解析当前请求对应的用户 ID，并缓存到 request.state。"""
    if hasattr(request.state, "user_id"):
        return request.state.user_id

    token = extract_bearer_token(authorization or request.headers.get("Authorization"))
    if not token:
        request.state.user_id = None
        return None

    user_id = await users.get_user_id_by_token(db, token)
    request.state.user_id = user_id
    request.state.auth_token = token
    return user_id


async def get_current_user(
    request: Request,
    authorization: str | None = Header(default=None),
    db: AsyncSession = Depends(get_db),
) -> User:
    """获取当前登录用户，用于需要认证的接口。"""
    token = extract_bearer_token(authorization)
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="缺少 Authorization header",
        )

    user = await users.get_user_by_token(db, token)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="无效的令牌或已经过期的令牌",
        )

    request.state.user_id = user.id
    request.state.auth_token = token
    return user
