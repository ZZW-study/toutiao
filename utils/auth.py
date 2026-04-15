"""认证与请求身份解析工具。"""

from __future__ import annotations

from fastapi import Depends, Header, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from configs.db import get_db
from crud import users
from models.users import User


def extract_bearer_token(authorization: str | None) -> str | None:
    """从 Authorization 头中提取 token。

    兼容两种写法：
    - `Bearer xxx`
    - 直接传 `xxx`
    """

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
    """解析当前请求对应的用户 ID，并回写到 `request.state`。

    这是认证依赖和限流依赖共享的统一身份解析入口。
    这样可以避免一个地方从 header 读 token，另一个地方再用完全不同的方式猜用户身份。
    """

    # 同一请求内如果已经解析过，就直接复用，避免重复查库。
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
    """获取当前登录用户。"""

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

    # 认证成功后，把 user_id 写回 request.state，供后续依赖直接复用。
    request.state.user_id = user.id
    request.state.auth_token = token
    return user
