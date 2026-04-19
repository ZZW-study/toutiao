# -*- coding: utf-8 -*-
"""浏览历史接口测试。"""

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_add_view_history_success(client: AsyncClient, auth_headers):
    """测试添加浏览历史（成功）。"""
    response = await client.post(
        "/api/history/add",
        headers=auth_headers,
        json={"newsId": 1}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200


@pytest.mark.asyncio
async def test_add_view_history_unauthorized(client: AsyncClient):
    """测试添加浏览历史（未授权）。"""
    response = await client.post(
        "/api/history/add",
        json={"newsId": 1}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_view_history_list_success(client: AsyncClient, auth_headers):
    """测试获取浏览历史列表（成功）。"""
    response = await client.get(
        "/api/history/list",
        params={"page": 1, "pageSize": 10},
        headers=auth_headers
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert "data" in data


@pytest.mark.asyncio
async def test_get_view_history_list_pagination(client: AsyncClient, auth_headers):
    """测试获取浏览历史列表（分页）。"""
    response = await client.get(
        "/api/history/list",
        params={"page": 1, "pageSize": 5},
        headers=auth_headers
    )
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_view_history_list_unauthorized(client: AsyncClient):
    """测试获取浏览历史列表（未授权）。"""
    response = await client.get(
        "/api/history/list",
        params={"page": 1, "pageSize": 10}
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_delete_view_history_success(client: AsyncClient, auth_headers):
    """测试删除浏览历史（成功）。"""
    response = await client.delete(
        "/api/history/delete/1",
        headers=auth_headers
    )
    assert response.status_code in [200, 404]


@pytest.mark.asyncio
async def test_delete_view_history_invalid_id(client: AsyncClient, auth_headers):
    """测试删除浏览历史（无效ID）。"""
    response = await client.delete(
        "/api/history/delete/0",
        headers=auth_headers
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_clear_view_history_success(client: AsyncClient, auth_headers):
    """测试清空浏览历史（成功）。"""
    response = await client.delete(
        "/api/history/clear",
        headers=auth_headers
    )
    assert response.status_code in [200, 404]
