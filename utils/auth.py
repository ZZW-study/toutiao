from fastapi import Header, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from configs.db_conf import get_db
from crud import users


async def get_current_user(
        authorization: str = Header(None),
        db: AsyncSession = Depends(get_db)
):
    if not authorization:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="缺少 Authorization header")
    parts = authorization.split()
    token = parts[1] if len(parts) == 2 else authorization
    user = await users.get_user_by_token(db, token)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="无效的令牌或已经过期的令牌")
    return user
