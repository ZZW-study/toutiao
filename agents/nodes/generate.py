# -*- coding: utf-8 -*-
"""回答生成节点。"""

from __future__ import annotations

from typing import Any

from agents.services import get_generate_service
from agents.state import AgentState

MAX_AGENT_LOOPS = 3


async def generate_node(state: AgentState) -> dict[str, Any]:
    """根据检索结果生成最终回答。"""

    result = await get_generate_service().generate(
        query=state["query"],
        news_list=state.get("news_list", []),
        loop_count=state.get("loop_count", 1),
        max_loops=MAX_AGENT_LOOPS,
    )
    return {
        "answer": result.answer,
        "is_satisfied": result.is_satisfied,
    }

