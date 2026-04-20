# -*- coding: utf-8 -*-
"""用户相关 HTTP 路由。

提供注册、登录、用户信息查询和修改等接口。
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from configs.db import get_db
from crud import users
from models.users import User
from schemas.users import (
    UserAuthResponse,
    UserChangePasswordRequest,
    UserInfoResponse,
    UserRequest,
    UserUpdateRequest,
)
from utils.auth import get_current_user
from utils.response import success_response

router = APIRouter(
    prefix="/api/user",
    tags=["users"],
)

# 1. 参数来源识别
# 当你在路由函数中声明一个参数（如 user_data: UserRequest）时，FastAPI 会按照固定顺序判断该参数应该从请求的哪个部分提取：
# 路径参数：如果参数名与路由路径中的 {变量} 同名 → 从 URL 路径提取
# 查询参数：如果不是路径参数，且为普通 Python 类型（如 str, int, bool 等）→ 从 URL 查询字符串提取
# 请求体参数：如果不是以上两种，且该类型是 Pydantic 模型（或 list, dict 等其他可解析类型）→ 从请求体（Body）中提取
# 因此，user_data: UserRequest 会被 FastAPI 自动判定为请求体参数，无需显式使用 Body(...)。
# 2. 自动解析 JSON 并校验
# 当请求到达时，FastAPI 会：
# 读取 request.json() 获取请求体的 JSON 数据
# 使用 UserRequest 这个 Pydantic 模型的 model_validate(json_data) 方法进行：
# 类型转换（如字符串转数字、日期时间）
# 字段验证（如 @field_validator、EmailStr、constraints 等）
# 嵌套模型解析
# 如果校验通过，生成一个 UserRequest 实例注入到 user_data 参数中
# 如果校验失败（缺少必填字段、类型错误、格式错误等），FastAPI 会自动返回 422 Unprocessable Entity 响应，并附带详细的错误信息（哪个字段、什么原因）
@router.post("/register")
async def register(user_data: UserRequest, db: AsyncSession = Depends(get_db)):
    """注册用户并返回登录态。"""
    existing_user = await users.get_user_by_username(db, user_data.username)
    if existing_user is not None:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户已存在")

    user = await users.create_user(db, user_data)
    token = await users.create_token(db, user.id)
    response_data = UserAuthResponse(
        token=token,
        user_info=UserInfoResponse.model_validate(user),
    )
    return success_response(message="注册成功", data=response_data)


@router.post("/login")
async def login(user_data: UserRequest, db: AsyncSession = Depends(get_db)):
    """用户名密码登录。"""
    user = await users.authenticate_user(db, user_data.username, user_data.password)

    if user == users.USER_NOT_FOUND:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=users.USER_NOT_FOUND)

    if user == users.INVALID_PASSWORD:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="输入密码错误，请重试")

    token = await users.create_token(db, user.id)
    response_data = UserAuthResponse(
        token=token,
        user_info=UserInfoResponse.model_validate(user),
    )
    return success_response(message="登录成功", data=response_data)


@router.get("/info")
async def get_user_info(user: User = Depends(get_current_user)):
    """获取当前登录用户信息。"""
    return success_response(message="获取用户信息成功", data=UserInfoResponse.model_validate(user))


@router.put("/update")
async def update_user_info(
    user_data: UserUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """更新当前用户资料。"""
    updated_user = await users.update_user(db, user.username, user_data)
    return success_response(
        message="更新用户信息成功",
        data=UserInfoResponse.model_validate(updated_user),
    )


@router.put("/password")
async def update_password(
    password_data: UserChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """修改当前用户密码。"""
    changed = await users.change_password(
        db,
        user,
        password_data.old_password,
        password_data.new_password,
    )
    if not changed:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="旧密码错误")

    return success_response(message="修改密码成功")
