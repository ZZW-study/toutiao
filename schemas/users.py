"""用户模块的请求与响应模型。"""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class UserRequest(BaseModel):
    """注册或登录时使用的基础用户请求体。"""

    username: str
    password: str


class UserUpdateRequest(BaseModel):
    """更新用户资料时的请求体。"""

    nickname: Optional[str] = None
    avatar: Optional[str] = None
    gender: Optional[str] = None
    bio: Optional[str] = None
    phone: Optional[str] = None


class UserChangePasswordRequest(BaseModel):
    """修改密码时的请求体。"""

    old_password: str = Field(..., alias="oldPassword", description="旧密码")
    new_password: str = Field(..., min_length=6, alias="newPassword", description="新密码")


class UserInfoBase(BaseModel):
    """用户公开资料基础字段。"""

    nickname: Optional[str] = Field(None, max_length=50, description="昵称")
    avatar: Optional[str] = Field(None, max_length=255, description="头像URL")
    gender: Optional[str] = Field(None, max_length=10, description="性别")
    bio: Optional[str] = Field(None, max_length=500, description="个人简介")


class UserInfoResponse(UserInfoBase):
    """用户资料响应体。"""

    id: int
    username: str

    model_config = ConfigDict(from_attributes=True)


class UserAuthResponse(BaseModel):
    """登录或注册成功后的响应体。"""

    token: str
    user_info: UserInfoResponse = Field(..., alias="userInfo")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )
