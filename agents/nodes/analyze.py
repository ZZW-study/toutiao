# -*- coding: utf-8 -*-
"""问题分析节点。"""

from __future__ import annotations

from typing import Any

from toutiao.agents.services.services import get_analyze_service
from agents.state import AgentState


async def analyze_node(state: AgentState) -> dict[str, Any]:
    """分析用户问题并生成检索条件。"""

    loop_count = state.get("loop_count", 0)
    result = await get_analyze_service().analyze(
        query=state["query"],
        loop_count=loop_count,
    )
    # 将分析结果写入状态，同时递增循环计数
    return {
        "keywords": result.keywords,
        "category": result.category,
        "search_query": result.search_query,
        "loop_count": loop_count + 1,
    }
