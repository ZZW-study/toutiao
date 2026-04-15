# -*- coding: utf-8 -*-
"""新闻检索节点。"""

from __future__ import annotations

from typing import Any

from agents.state import AgentState
from agents.tools.news_retriever import get_news_retriever_service


async def retrieve_node(state: AgentState) -> dict[str, Any]:
    """根据分析结果检索新闻。"""

    loop_count = state.get("loop_count", 1)
    top_k = min(5 + max(loop_count - 1, 0) * 2, 15)
    news_list = await get_news_retriever_service().search_news(
        query=state.get("search_query", ""),
        category=state.get("category"),
        top_k=top_k,
    )
    return {"news_list": news_list}

