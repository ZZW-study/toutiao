# -*- coding: utf-8 -*-
"""用户接口测试。"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    """注册成功后应返回 token 与用户信息。"""

    response = await client.post(
        "/api/user/register",
        json={"username": "newuser", "password": "password123"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["code"] == 200
    assert "data" in data
    assert "token" in data["data"]
    assert "userInfo" in data["data"]


@pytest.mark.asyncio
async def test_register_duplicate_username(client: AsyncClient, test_user):
    """重复用户名注册应被拒绝。"""

    response = await client.post(
        "/api/user/register",
        json={"username": "testuser", "password": "password123"},
    )
    assert response.status_code == 400
    assert "message" in response.json()


@pytest.mark.asyncio
async def test_register_missing_fields(client: AsyncClient):
    """缺少必填字段时应命中 Pydantic 校验。"""

    response = await client.post(
        "/api/user/register",
        json={"username": "newuser"},
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user):
    """用户名和密码正确时应登录成功。"""

    response = await client.post(
        "/api/user/login",
        json={"username": "testuser", "password": "testpass123"},
    )
    assert response.status_code == 200

    data = response.json()
    assert data["code"] == 200
    assert "token" in data["data"]


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_user):
    """密码错误时应返回 401。"""

    response = await client.post(
        "/api/user/login",
        json={"username": "testuser", "password": "wrongpassword"},
    )
    assert response.status_code == 401
    assert "message" in response.json()


@pytest.mark.asyncio
async def test_login_user_not_found(client: AsyncClient):
    """不存在的用户登录应返回 404。"""

    response = await client.post(
        "/api/user/login",
        json={"username": "nonexistent", "password": "password123"},
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_user_info_success(client: AsyncClient, auth_headers):
    """带有效 token 时应能拿到当前用户信息。"""

    response = await client.get("/api/user/info", headers=auth_headers)
    assert response.status_code == 200

    data = response.json()
    assert data["code"] == 200
    assert "data" in data


@pytest.mark.asyncio
async def test_get_user_info_unauthorized(client: AsyncClient):
    """未登录访问用户信息应返回 401。"""

    response = await client.get("/api/user/info")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_user_success(client: AsyncClient, auth_headers):
    """更新用户资料接口应正常返回成功。"""

    response = await client.put(
        "/api/user/update",
        headers=auth_headers,
        json={"username": "updated"},
    )

    # 当前 schema 不接收 username 字段，Pydantic 会忽略它；
    # 因此请求虽然没有真正修改字段，但接口流程仍应稳定返回成功。
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_update_password_success(client: AsyncClient, auth_headers):
    """旧密码正确时应能修改密码。"""

    response = await client.put(
        "/api/user/password",
        headers=auth_headers,
        json={"oldPassword": "testpass123", "newPassword": "newpass123"},
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_update_password_wrong_old(client: AsyncClient, auth_headers):
    """旧密码错误时应返回 400。"""

    response = await client.put(
        "/api/user/password",
        headers=auth_headers,
        json={"oldPassword": "wrongpass", "newPassword": "newpass123"},
    )
    assert response.status_code == 400
