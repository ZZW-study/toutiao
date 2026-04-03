# -*- coding: utf-8 -*-
"""
收藏接口测试
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_check_favorite_success(client: AsyncClient, auth_headers):
    """测试检查收藏状态（成功）"""
    response = await client.get(
        "/api/favorite/check",
        params={"newsId": 1},
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert "data" in data
    assert "isFavorite" in data["data"]


@pytest.mark.asyncio
async def test_check_favorite_unauthorized(client: AsyncClient):
    """测试检查收藏状态（未授权）"""
    response = await client.get(
        "/api/favorite/check",
        params={"newsId": 1}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_add_favorite_success(client: AsyncClient, auth_headers):
    """测试添加收藏（成功）"""
    response = await client.post(
        "/api/favorite/add",
        headers=auth_headers,
        json={"newsId": 1}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200


@pytest.mark.asyncio
async def test_add_favorite_duplicate(client: AsyncClient, auth_headers):
    """测试添加收藏（重复收藏）"""
    await client.post(
        "/api/favorite/add",
        headers=auth_headers,
        json={"newsId": 2}
    )
    response = await client.post(
        "/api/favorite/add",
        headers=auth_headers,
        json={"newsId": 2}
    )
    assert response.status_code in [200, 400, 500]


@pytest.mark.asyncio
async def test_remove_favorite_success(client: AsyncClient, auth_headers):
    """测试取消收藏（成功）"""
    await client.post(
        "/api/favorite/add",
        headers=auth_headers,
        json={"newsId": 3}
    )
    response = await client.delete(
        "/api/favorite/remove",
        params={"newsId": 3},
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200


@pytest.mark.asyncio
async def test_remove_favorite_not_found(client: AsyncClient, auth_headers):
    """测试取消收藏（记录不存在）"""
    response = await client.delete(
        "/api/favorite/remove",
        params={"newsId": 99999},
        headers=auth_headers
    )
    assert response.status_code in [200, 404]


@pytest.mark.asyncio
async def test_get_favorite_list_success(client: AsyncClient, auth_headers):
    """测试获取收藏列表（成功）"""
    response = await client.get(
        "/api/favorite/list",
        params={"page": 1, "pageSize": 10},
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert "data" in data
    assert "list" in data["data"]
    assert "total" in data["data"]


@pytest.mark.asyncio
async def test_get_favorite_list_pagination(client: AsyncClient, auth_headers):
    """测试获取收藏列表（分页）"""
    response = await client.get(
        "/api/favorite/list",
        params={"page": 1, "pageSize": 5},
        headers=auth_headers
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_clear_favorites_success(client: AsyncClient, auth_headers):
    """测试清空收藏（成功）"""
    response = await client.delete(
        "/api/favorite/clear",
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
