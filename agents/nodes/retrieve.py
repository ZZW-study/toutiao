# -*- coding: utf-8 -*-
"""新闻检索节点。"""

from __future__ import annotations

from typing import Any

from agents.state import AgentState
from agents.services.news_retriever import get_news_retriever_service


async def retrieve_node(state: AgentState) -> dict[str, Any]:
    """根据分析结果检索新闻。"""

    # 使用分析阶段产出的关键词和分类进行检索
    news_list = await get_news_retriever_service().search_news(
        query=state.get("search_query", state["query"]),
        category=state.get("category"),
    )
    return {"news_list": news_list}
