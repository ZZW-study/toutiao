# 用户管理模块
from typing import Optional
from pydantic import BaseModel, ConfigDict,Field # Pydantic 核心：先定义规则（模型），再校验数据，通过则实例化，失败则返回结构化错误

# 第一部分，请求体参数模型

#用户注册需要输入的请求体类
class UserRequest(BaseModel):
    username:str
    password:str

# 更新用户信息的模型类
class UserUpdateRequest(BaseModel):
    nickname: Optional[str] = None
    avatar: Optional[str] = None
    gender: Optional[str] = None
    bio: Optional[str] = None
    phone: Optional[str] = None


# 修改用户密码的模型类
class UserChangePasswordRequest(BaseModel):
    old_password: str = Field(...,alias="oldPassword",description="旧密码")
    new_password: str = Field(...,min_length=6,alias="newPassword",description="新密码")

# 第二部分，响应体参数模型

#用户信息基础数据模型类--user_info对应的类
class UserInfoBase(BaseModel):
    nickname: Optional[str]=Field(None, max_length=50, description="昵称")
    avatar: Optional[str]=Field(None, max_length=255, description="头像URL")
    gender: Optional[str]=Field(None, max_length=10, description="性别")
    bio: Optional[str]=Field(None, max_length=500, description="个人简介")

#用户信息响应模型
class UserInfoResponse(UserInfoBase):
    id: int
    username: str
    model_config = ConfigDict(
        # 允许从 ORM 对象（如 SQLAlchemy 模型实例）中直接提取属性值，
        from_attributes=True
    ) 

# 定义用户认证响应模型，用于登录/注册等认证场景的返回数据结构
class UserAuthResponse(BaseModel):
    token: str
    user_info: UserInfoResponse = Field(..., alias="userInfo")

    model_config = ConfigDict(
        # 允许通过 Python 原生字段名（如 user_info）填充数据，同时支持别名（userInfo）的序列化/反序列化
        populate_by_name=True,
        # 保持 ORM 兼容性，支持从 ORM 对象自动转换为 Pydantic 模型
        from_attributes=True
    )



    







