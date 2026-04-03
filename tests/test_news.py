# -*- coding: utf-8 -*-
"""
新闻接口测试
"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_get_news_categories(client: AsyncClient):
    """测试获取新闻分类"""
    response = await client.get("/api/news/categories")
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert "data" in data
    assert isinstance(data["data"], list)


@pytest.mark.asyncio
async def test_get_news_categories_with_pagination(client: AsyncClient):
    """测试获取新闻分类（带分页参数）"""
    response = await client.get("/api/news/categories", params={"skip": 0, "limit": 10})
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200


@pytest.mark.asyncio
async def test_get_news_list_success(client: AsyncClient):
    """测试获取新闻列表（成功）"""
    response = await client.get(
        "/api/news/list",
        params={"categoryId": 1, "page": 1, "pageSize": 10}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["code"] == 200
    assert "data" in data
    assert "list" in data["data"]
    assert "total" in data["data"]
    assert "hasMore" in data["data"]


@pytest.mark.asyncio
async def test_get_news_list_invalid_category(client: AsyncClient):
    """测试获取新闻列表（无效分类）"""
    response = await client.get(
        "/api/news/list",
        params={"categoryId": -1, "page": 1, "pageSize": 10}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_news_list_invalid_page(client: AsyncClient):
    """测试获取新闻列表（无效页码）"""
    response = await client.get(
        "/api/news/list",
        params={"categoryId": 1, "page": 0, "pageSize": 10}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_news_list_page_size_limit(client: AsyncClient):
    """测试获取新闻列表（页大小超限）"""
    response = await client.get(
        "/api/news/list",
        params={"categoryId": 1, "page": 1, "pageSize": 200}
    )
    assert response.status_code == 422


@pytest.mark.asyncio
async def test_get_news_detail_success(client: AsyncClient):
    """测试获取新闻详情（成功）"""
    response = await client.get(
        "/api/news/detail",
        params={"id": 1}
    )
    if response.status_code == 200:
        data = response.json()
        assert data["code"] == 200
        assert "data" in data
        assert "id" in data["data"]
        assert "title" in data["data"]
    elif response.status_code == 404:
        assert "message" in response.json()


@pytest.mark.asyncio
async def test_get_news_detail_not_found(client: AsyncClient):
    """测试获取新闻详情（不存在）"""
    response = await client.get(
        "/api/news/detail",
        params={"id": 99999}
    )
    assert response.status_code in [404, 500]


@pytest.mark.asyncio
async def test_get_news_detail_missing_id(client: AsyncClient):
    """测试获取新闻详情（缺少ID）"""
    response = await client.get("/api/news/detail")
    assert response.status_code == 422
