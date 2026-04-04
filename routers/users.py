"""用户相关 HTTP 路由定义。

说明：路由层负责：参数校验、鉴权依赖注入、限流（中间件/依赖）、调用 CRUD 层并返回统一响应。

路由：
- POST `/register`：注册新用户
- POST `/login`：用户名/密码登录，返回 token
- GET `/info`：获取当前登录用户信息
- PUT `/update`：更新用户信息
- PUT `/password`：修改密码
"""

from fastapi import APIRouter, Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from utils.response import success_response
from configs.db_conf import get_db
from crud import users
from schemas.users import (
    UserRequest,
    UserAuthResponse,
    UserInfoResponse,
    UserUpdateRequest,
    UserChangePasswordRequest,
)
from utils.auth import get_current_user
from models.users import User
from middlewares.token_bucket_rate_limit import rate_limit_dependency


router = APIRouter(prefix="/api/user", tags=["users"])


@router.post("/register")
async def register(user_data: UserRequest, db: AsyncSession = Depends(get_db)):
    """注册新用户。

    - 输入：`UserRequest`（包含 `username`、`password` 等）
    - 逻辑：检查用户名是否存在 -> 创建用户 -> 生成 token
    - 返回：`UserAuthResponse`，包含 `token` 与 `user_info`
    """
    existing_user = await users.get_user_by_username(db, user_data.username)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户已存在")
    user = await users.create_user(db, user_data)
    token = await users.create_token(db, user.id)

    response_data = UserAuthResponse(token=token, user_info=UserInfoResponse.model_validate(user))
    return success_response(message="注册成功", data=response_data)


@router.post("/login")
async def login(user_data: UserRequest, db: AsyncSession = Depends(get_db)):
    """用户登录。

    - 使用 `authenticate_user` 校验用户名和密码，函数会返回 `User` 或错误字符串。
    - 失败时转换为合适的 HTTP 错误码（404/401）。
    - 成功后生成新的 token 并返回认证信息。
    """
    user = await users.authenticate_user(db, user_data.username, user_data.password)

    if user == "用户不存在":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

    if user == "用户密码错误":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="输入密码错误，请重试")

    token = await users.create_token(db, user.id)
    response_data = UserAuthResponse(token=token, user_info=UserInfoResponse.model_validate(user))

    return success_response(message="登录成功", data=response_data)


@router.get("/info")
async def get_user_info(
    request: Request,
    user: User = Depends(get_current_user),
    _: None = Depends(rate_limit_dependency)
):
    """返回当前登录用户信息。

    - 依赖注入 `get_current_user` 用于鉴权并把 `User` 实例注入到参数中。
    - 同时使用限流依赖防止滥用接口。
    """
    return success_response(message="获取用户信息成功", data=UserInfoResponse.model_validate(user))


@router.put("/update")
async def update_user_info(
    user_data: UserUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_dependency)
):
    """更新当前用户的信息。

    - 仅登录用户可访问（依赖 `get_current_user`）。
    - 更新成功后返回最新的 `UserInfoResponse`。
    """
    user = await users.update_user(db, user.username, user_data)
    return success_response(message="更新用户信息成功", data=UserInfoResponse.model_validate(user))


@router.put("/password")
async def update_password(
    request: Request,
    password_data: UserChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_dependency)
):
    """修改当前用户密码。

    - 验证旧密码是否正确，正确则保存新密码并删除相关缓存。
    - 返回修改结果。修改失败（例如旧密码错误）会抛出相应 HTTP 错误。
    """
    res_change_pwd = await users.change_password(db, user, password_data.old_password, password_data.new_password)
    if not res_change_pwd:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="修改密码失败，请稍后再试")
    return success_response(message="修改密码成功")