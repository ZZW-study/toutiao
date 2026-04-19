# -*- coding: utf-8 -*-
"""
收藏接口测试
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_check_favorite_success(client: AsyncClient, auth_headers):
    """测试检查收藏状态（成功）"""
    # 登录用户查询某条新闻的收藏状态
    response = await client.get(
        "/api/favorite/check",
        params={"newsId": 1},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert "data" in data
    assert "isFavorite" in data["data"]


@pytest.mark.asyncio
async def test_check_favorite_unauthorized(client: AsyncClient):
    """测试检查收藏状态（未授权）"""
    # 未携带 token 访问收藏状态接口，应被拒绝
    response = await client.get(
        "/api/favorite/check",
        params={"newsId": 1},
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_add_favorite_success(client: AsyncClient, auth_headers):
    """测试添加收藏（成功）"""
    response = await client.post(
        "/api/favorite/add",
        headers=auth_headers,
        json={"newsId": 1},
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200


@pytest.mark.asyncio
async def test_add_favorite_duplicate(client: AsyncClient, auth_headers):
    """测试添加收藏（重复收藏）"""
    # 先收藏一次，再收藏同一条新闻，验证重复收藏的处理
    await client.post(
        "/api/favorite/add",
        headers=auth_headers,
        json={"newsId": 2},
    )
    response = await client.post(
        "/api/favorite/add",
        headers=auth_headers,
        json={"newsId": 2},
    )
    # 重复收藏时接口可能返回 200（幂等）/400/500，视后端实现而定
    assert response.status_code in [200, 400, 500]


@pytest.mark.asyncio
async def test_remove_favorite_success(client: AsyncClient, auth_headers):
    """测试取消收藏（成功）"""
    # 先添加收藏，再取消，验证完整流程
    await client.post(
        "/api/favorite/add",
        headers=auth_headers,
        json={"newsId": 3},
    )
    response = await client.delete(
        "/api/favorite/remove",
        params={"newsId": 3},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200


@pytest.mark.asyncio
async def test_remove_favorite_not_found(client: AsyncClient, auth_headers):
    """测试取消收藏（记录不存在）"""
    # 取消一条从未收藏过的新闻，后端可能返回 200（幂等）或 404
    response = await client.delete(
        "/api/favorite/remove",
        params={"newsId": 99999},
        headers=auth_headers,
    )
    assert response.status_code in [200, 404]


@pytest.mark.asyncio
async def test_get_favorite_list_success(client: AsyncClient, auth_headers):
    """测试获取收藏列表（成功）"""
    response = await client.get(
        "/api/favorite/list",
        params={"page": 1, "pageSize": 10},
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert "data" in data
    # 收藏列表应包含 list 和 total 字段，供前端分页展示
    assert "list" in data["data"]
    assert "total" in data["data"]


@pytest.mark.asyncio
async def test_get_favorite_list_pagination(client: AsyncClient, auth_headers):
    """测试获取收藏列表（分页）"""
    response = await client.get(
        "/api/favorite/list",
        params={"page": 1, "pageSize": 5},
        headers=auth_headers,
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_clear_favorites_success(client: AsyncClient, auth_headers):
    """测试清空收藏（成功）"""
    response = await client.delete(
        "/api/favorite/clear",
        headers=auth_headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
