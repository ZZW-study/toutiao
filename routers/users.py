#用户路由
from fastapi import APIRouter, Depends, HTTPException,status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from utils.response import success_response
from configs.db_conf import get_db
from crud import users
from schemas.users import UserRequest, UserAuthResponse, UserInfoResponse, UserUpdateRequest,UserChangePasswordRequest
from utils.auth import get_current_user
from models.users import User
from middlewares.token_bucket_rate_limit import rate_limit_dependency

router = APIRouter(prefix="/api/user",tags=["users"])


@router.post("/register")
async def register(user_data: UserRequest, db: AsyncSession = Depends(get_db)):
    existing_user = await users.get_user_by_username(db, user_data.username)
    if existing_user:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="用户已存在")
    user = await users.create_user(db, user_data)
    token = await users.create_token(db, user.id)

    response_data = UserAuthResponse(token=token, user_info=UserInfoResponse.model_validate(user))
    return success_response(message="注册成功", data=response_data)


@router.post("/login")
async def login(user_data: UserRequest, db: AsyncSession = Depends(get_db)):
    user = await users.authenticate_user(db,user_data.username,user_data.password)

    if user == "用户不存在":
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="用户不存在")

    if user == "用户密码错误":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,detail="输入密码错误，请重试")

    token = await users.create_token(db,user.id)
    response_data = UserAuthResponse(token=token,user_info=UserInfoResponse.model_validate(user))

    return success_response(message="登录成功",data=response_data)


@router.get("/info")
async def get_user_info(
    request: Request,
    user: User = Depends(get_current_user),
    _: None = Depends(rate_limit_dependency)
):
    return success_response(message="获取用户信息成功",data=UserInfoResponse.model_validate(user))


@router.put("/update")
async def update_user_info(
    user_data: UserUpdateRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_dependency)
):
    user = await users.update_user(db,user.username,user_data)
    return success_response(message="更新用户信息成功",data=UserInfoResponse.model_validate(user))


@router.put("/password")
async def update_password(
    request: Request,
    password_data: UserChangePasswordRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_dependency)
):
    res_change_pwd = await users.change_password(db,user,password_data.old_password,password_data.new_password)
    if not res_change_pwd:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,detail="修改密码失败，请稍后再试")
    return success_response(message="修改密码成功")