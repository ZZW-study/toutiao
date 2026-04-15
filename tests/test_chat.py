# -*- coding: utf-8 -*-
"""聊天路由测试。"""

from __future__ import annotations

import pytest
from httpx import AsyncClient

import indexer
import routers.chat as chat_router


class _FakeAgentRunner:
    """用假的 Agent Runner 替代真实工作流，方便隔离聊天路由测试。"""
    def __init__(self, result=None, error: Exception | None = None):
        """初始化测试用的返回值或异常对象。"""
        self._result = result or {}
        self._error = error

    async def ainvoke(self, initial_state, session_id=None):
        """模拟 Agent 的异步执行接口，按测试需要返回结果或抛错。"""
        if self._error is not None:
            raise self._error
        return self._result


@pytest.mark.asyncio
async def test_chat_success(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    """聊天接口应返回标准化回答结构。"""

    monkeypatch.setattr(
        chat_router,
        "get_agent_runner",
        lambda: _FakeAgentRunner(
            {
                "answer": "这是基于检索结果整理出的回答。",
                "loop_count": 1,
                "news_list": [
                    {
                        "id": 1,
                        "title": "测试新闻",
                        "content": "测试内容",
                        "description": "测试摘要",
                        "category_id": 1,
                        "publish_time": "2024-01-01T00:00:00",
                        "image": None,
                        "author": "测试作者",
                    }
                ],
            }
        ),
    )

    response = await client.post("/chat/", json={"query": "帮我总结一下今天的新闻"})
    assert response.status_code == 200
    data = response.json()
    assert data["answer"] == "这是基于检索结果整理出的回答。"
    assert data["loop_count"] == 1
    assert len(data["news_list"]) == 1
    assert data["news_list"][0]["title"] == "测试新闻"


@pytest.mark.asyncio
async def test_chat_failure_returns_500(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    """Agent 异常时应返回 500。"""

    monkeypatch.setattr(
        chat_router,
        "get_agent_runner",
        lambda: _FakeAgentRunner(error=RuntimeError("agent failed")),
    )

    response = await client.post("/chat/", json={"query": "测试异常路径"})
    assert response.status_code == 500
    data = response.json()
    assert data["code"] == 500
    assert "处理请求失败" in data["message"]


@pytest.mark.asyncio
async def test_chat_stats(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    """统计接口应返回向量库信息。"""

    monkeypatch.setattr(
        chat_router,
        "get_vectorstore_stats",
        lambda: {"total_vectors": 12, "persist_directory": "data/chroma"},
    )

    response = await client.get("/chat/stats")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["vector_count"] == 12


@pytest.mark.asyncio
async def test_chat_index(client: AsyncClient, monkeypatch: pytest.MonkeyPatch):
    """手动索引接口应能调用索引器。"""

    async def fake_index_all_news():
        """模拟全量索引任务，避免测试时真正访问向量库。"""
        return {"total": 1, "indexed": 1, "skipped": 0}

    monkeypatch.setattr(indexer, "index_all_news", fake_index_all_news)

    response = await client.post("/chat/index")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "ok"
    assert data["result"]["indexed"] == 1
