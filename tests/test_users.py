# -*- coding: utf-8 -*-
"""用户接口测试。"""

import pytest  # 导入 pytest 模块，给当前文件后面的逻辑使用
from httpx import AsyncClient  # 从 httpx 模块导入当前文件后续要用到的对象


@pytest.mark.asyncio  # 使用 pytest.mark.asyncio 装饰下面的函数或类，给它附加额外能力
async def test_register_success(client: AsyncClient):  # 定义异步函数 test_register_success，调用它时通常需要配合 await 使用
    """注册成功后应返回 token 与用户信息。"""

    response = await client.post(  # 把右边计算出来的结果保存到 response 变量中，方便后面的代码继续复用
        "/api/user/register",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        json={"username": "newuser", "password": "password123"},  # 把右边计算出来的结果保存到 json 变量中，方便后面的代码继续复用
    )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
    assert response.status_code == 200  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题

    data = response.json()  # 把右边计算出来的结果保存到 data 变量中，方便后面的代码继续复用
    assert data["code"] == 200  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
    assert "data" in data  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
    assert "token" in data["data"]  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
    assert "userInfo" in data["data"]  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题


@pytest.mark.asyncio  # 使用 pytest.mark.asyncio 装饰下面的函数或类，给它附加额外能力
async def test_register_duplicate_username(client: AsyncClient, test_user):  # 定义异步函数 test_register_duplicate_username，调用它时通常需要配合 await 使用
    """重复用户名注册应被拒绝。"""

    response = await client.post(  # 把右边计算出来的结果保存到 response 变量中，方便后面的代码继续复用
        "/api/user/register",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        json={"username": "testuser", "password": "password123"},  # 把右边计算出来的结果保存到 json 变量中，方便后面的代码继续复用
    )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
    assert response.status_code == 400  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
    assert "message" in response.json()  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题


@pytest.mark.asyncio  # 使用 pytest.mark.asyncio 装饰下面的函数或类，给它附加额外能力
async def test_register_missing_fields(client: AsyncClient):  # 定义异步函数 test_register_missing_fields，调用它时通常需要配合 await 使用
    """缺少必填字段时应命中 Pydantic 校验。"""

    response = await client.post(  # 把右边计算出来的结果保存到 response 变量中，方便后面的代码继续复用
        "/api/user/register",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        json={"username": "newuser"},  # 把右边计算出来的结果保存到 json 变量中，方便后面的代码继续复用
    )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
    assert response.status_code == 422  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题


@pytest.mark.asyncio  # 使用 pytest.mark.asyncio 装饰下面的函数或类，给它附加额外能力
async def test_login_success(client: AsyncClient, test_user):  # 定义异步函数 test_login_success，调用它时通常需要配合 await 使用
    """用户名和密码正确时应登录成功。"""

    response = await client.post(  # 把右边计算出来的结果保存到 response 变量中，方便后面的代码继续复用
        "/api/user/login",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        json={"username": "testuser", "password": "testpass123"},  # 把右边计算出来的结果保存到 json 变量中，方便后面的代码继续复用
    )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
    assert response.status_code == 200  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题

    data = response.json()  # 把右边计算出来的结果保存到 data 变量中，方便后面的代码继续复用
    assert data["code"] == 200  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
    assert "token" in data["data"]  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题


@pytest.mark.asyncio  # 使用 pytest.mark.asyncio 装饰下面的函数或类，给它附加额外能力
async def test_login_wrong_password(client: AsyncClient, test_user):  # 定义异步函数 test_login_wrong_password，调用它时通常需要配合 await 使用
    """密码错误时应返回 401。"""

    response = await client.post(  # 把右边计算出来的结果保存到 response 变量中，方便后面的代码继续复用
        "/api/user/login",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        json={"username": "testuser", "password": "wrongpassword"},  # 把右边计算出来的结果保存到 json 变量中，方便后面的代码继续复用
    )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
    assert response.status_code == 401  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
    assert "message" in response.json()  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题


@pytest.mark.asyncio  # 使用 pytest.mark.asyncio 装饰下面的函数或类，给它附加额外能力
async def test_login_user_not_found(client: AsyncClient):  # 定义异步函数 test_login_user_not_found，调用它时通常需要配合 await 使用
    """不存在的用户登录应返回 404。"""

    response = await client.post(  # 把右边计算出来的结果保存到 response 变量中，方便后面的代码继续复用
        "/api/user/login",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        json={"username": "nonexistent", "password": "password123"},  # 把右边计算出来的结果保存到 json 变量中，方便后面的代码继续复用
    )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
    assert response.status_code == 404  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题


@pytest.mark.asyncio  # 使用 pytest.mark.asyncio 装饰下面的函数或类，给它附加额外能力
async def test_get_user_info_success(client: AsyncClient, auth_headers):  # 定义异步函数 test_get_user_info_success，调用它时通常需要配合 await 使用
    """带有效 token 时应能拿到当前用户信息。"""

    response = await client.get("/api/user/info", headers=auth_headers)  # 把右边计算出来的结果保存到 response 变量中，方便后面的代码继续复用
    assert response.status_code == 200  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题

    data = response.json()  # 把右边计算出来的结果保存到 data 变量中，方便后面的代码继续复用
    assert data["code"] == 200  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
    assert "data" in data  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题


@pytest.mark.asyncio  # 使用 pytest.mark.asyncio 装饰下面的函数或类，给它附加额外能力
async def test_get_user_info_unauthorized(client: AsyncClient):  # 定义异步函数 test_get_user_info_unauthorized，调用它时通常需要配合 await 使用
    """未登录访问用户信息应返回 401。"""

    response = await client.get("/api/user/info")  # 把右边计算出来的结果保存到 response 变量中，方便后面的代码继续复用
    assert response.status_code == 401  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题


@pytest.mark.asyncio  # 使用 pytest.mark.asyncio 装饰下面的函数或类，给它附加额外能力
async def test_update_user_success(client: AsyncClient, auth_headers):  # 定义异步函数 test_update_user_success，调用它时通常需要配合 await 使用
    """更新用户资料接口应正常返回成功。"""

    response = await client.put(  # 把右边计算出来的结果保存到 response 变量中，方便后面的代码继续复用
        "/api/user/update",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        headers=auth_headers,  # 把右边计算出来的结果保存到 headers 变量中，方便后面的代码继续复用
        json={"username": "updated"},  # 把右边计算出来的结果保存到 json 变量中，方便后面的代码继续复用
    )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级

    # 当前 schema 不接收 username 字段，Pydantic 会忽略它；
    # 因此请求虽然没有真正修改字段，但接口流程仍应稳定返回成功。
    assert response.status_code == 200  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题


@pytest.mark.asyncio  # 使用 pytest.mark.asyncio 装饰下面的函数或类，给它附加额外能力
async def test_update_password_success(client: AsyncClient, auth_headers):  # 定义异步函数 test_update_password_success，调用它时通常需要配合 await 使用
    """旧密码正确时应能修改密码。"""

    response = await client.put(  # 把右边计算出来的结果保存到 response 变量中，方便后面的代码继续复用
        "/api/user/password",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        headers=auth_headers,  # 把右边计算出来的结果保存到 headers 变量中，方便后面的代码继续复用
        json={"oldPassword": "testpass123", "newPassword": "newpass123"},  # 把右边计算出来的结果保存到 json 变量中，方便后面的代码继续复用
    )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
    assert response.status_code == 200  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题


@pytest.mark.asyncio  # 使用 pytest.mark.asyncio 装饰下面的函数或类，给它附加额外能力
async def test_update_password_wrong_old(client: AsyncClient, auth_headers):  # 定义异步函数 test_update_password_wrong_old，调用它时通常需要配合 await 使用
    """旧密码错误时应返回 400。"""

    response = await client.put(  # 把右边计算出来的结果保存到 response 变量中，方便后面的代码继续复用
        "/api/user/password",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        headers=auth_headers,  # 把右边计算出来的结果保存到 headers 变量中，方便后面的代码继续复用
        json={"oldPassword": "wrongpass", "newPassword": "newpass123"},  # 把右边计算出来的结果保存到 json 变量中，方便后面的代码继续复用
    )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
    assert response.status_code == 400  # 断言这一行条件必须成立，如果不成立就说明测试或逻辑出现了问题
