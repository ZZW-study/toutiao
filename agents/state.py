# -*- coding: utf-8 -*-
"""Agent 状态定义。

用 TypedDict 声明工作流各节点间传递的字段，
LangGraph 会自动把每个节点返回的 dict 合并到全局状态中。
"""

from __future__ import annotations

from typing import Any, TypedDict


class AgentState(TypedDict, total=False):
    """新闻问答 Agent 的全局状态。"""

    query: str
    keywords: list[str]
    category: str | None
    search_query: str
    news_list: list[dict[str, Any]]
    answer: str
    is_satisfied: bool
    loop_count: int
