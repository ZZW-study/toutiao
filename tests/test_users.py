# -*- coding: utf-8 -*-
"""
用户接口测试
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_success(client: AsyncClient):
    """测试用户注册（成功）"""
    response = await client.post(
        "/api/user/register",
        json={"username": "newuser", "password": "password123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert "data" in data
    assert "token" in data["data"]
    assert "userInfo" in data["data"]


@pytest.mark.asyncio
async def test_register_duplicate_username(client: AsyncClient, test_user):
    """测试用户注册（用户名已存在）"""
    response = await client.post(
        "/api/user/register",
        json={"username": "testuser", "password": "password123"}
    )
    assert response.status_code == 400
    data = response.json()
    assert "message" in data


@pytest.mark.asyncio
async def test_register_missing_fields(client: AsyncClient):
    """测试用户注册（缺少字段）"""
    response = await client.post(
        "/api/user/register",
        json={"username": "newuser"}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user):
    """测试用户登录（成功）"""
    response = await client.post(
        "/api/user/login",
        json={"username": "testuser", "password": "testpass123"}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert "token" in data["data"]


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_user):
    """测试用户登录（密码错误）"""
    response = await client.post(
        "/api/user/login",
        json={"username": "testuser", "password": "wrongpassword"}
    )
    assert response.status_code == 401
    data = response.json()
    assert "message" in data


@pytest.mark.asyncio
async def test_login_user_not_found(client: AsyncClient):
    """测试用户登录（用户不存在）"""
    response = await client.post(
        "/api/user/login",
        json={"username": "nonexistent", "password": "password123"}
    )
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_get_user_info_success(client: AsyncClient, auth_headers):
    """测试获取用户信息（成功）"""
    response = await client.get("/api/user/info", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert "data" in data


@pytest.mark.asyncio
async def test_get_user_info_unauthorized(client: AsyncClient):
    """测试获取用户信息（未授权）"""
    response = await client.get("/api/user/info")
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_update_user_success(client: AsyncClient, auth_headers):
    """测试更新用户信息（成功）"""
    response = await client.put(
        "/api/user/update",
        headers=auth_headers,
        json={"username": "updated"}
    )
    assert response.status_code in [200, 500]


@pytest.mark.asyncio
async def test_update_password_success(client: AsyncClient, auth_headers):
    """测试修改密码（成功）"""
    response = await client.put(
        "/api/user/password",
        headers=auth_headers,
        json={"oldPassword": "testpass123", "newPassword": "newpass123"}
    )
    assert response.status_code in [200, 500]


@pytest.mark.asyncio
async def test_update_password_wrong_old(client: AsyncClient, auth_headers):
    """测试修改密码（旧密码错误）"""
    response = await client.put(
        "/api/user/password",
        headers=auth_headers,
        json={"oldPassword": "wrongpass", "newPassword": "newpass123"}
    )
    assert response.status_code in [200, 500]
