# -*- coding: utf-8 -*-
"""Agent 工作流入口。"""

from __future__ import annotations

import asyncio
from typing import Any

from langgraph.graph import END, StateGraph

from agents.nodes.analyze import analyze_node
from agents.nodes.generate import generate_node
from agents.nodes.retrieve import retrieve_node
from agents.state import AgentState
from utils.logger import get_logger

logger = get_logger(name="AgentGraph")


def should_continue(state: AgentState) -> str:
    """决定是结束还是继续重试。"""

    # 用户已满意或重试次数达到上限则结束，否则继续重试
    if state.get("is_satisfied", False):
        return "end"

    if state.get("loop_count", 0) >= 3:
        return "end"

    return "retry"


class NewsQaAgentRunner:
    """延迟构建的新闻问答 Agent。

    这里保留 LangGraph 的编排优势，但去掉了模块导入时的全局初始化和未实际使用的
    `MemorySaver`，让 Web 应用和 AI 栈的耦合更小。
    """

    def __init__(self) -> None:
        """初始化 Runner，并准备延迟构建工作流所需的内部状态。"""
        self._graph = None
        # 异步锁保证并发场景下工作流只构建一次
        self._build_lock = asyncio.Lock()

    def _build_graph_sync(self):
        """同步构建 LangGraph 工作流，把节点和边一次性串起来。"""
        # 定义工作流：分析 -> 检索 -> 生成，生成后根据条件决定结束或重试
        workflow = StateGraph(AgentState)
        workflow.add_node("analyze", analyze_node)
        workflow.add_node("retrieve", retrieve_node)
        workflow.add_node("generate", generate_node)
        workflow.set_entry_point("analyze")
        workflow.add_edge("analyze", "retrieve")
        workflow.add_edge("retrieve", "generate")
        workflow.add_conditional_edges(
            "generate",
            should_continue,
            {"end": END, "retry": "analyze"},
        )
        logger.info("新闻问答 Agent 工作流已构建")
        return workflow.compile()

    async def _get_graph(self):
        """懒加载并返回编译后的工作流实例。"""
        if self._graph is not None:
            return self._graph

        # 双重检查锁，避免并发时重复构建
        async with self._build_lock:
            if self._graph is None:
                self._graph = self._build_graph_sync()
        return self._graph

    async def ainvoke(
        self,
        initial_state: dict[str, Any],
        session_id: str | None = None,
    ) -> dict[str, Any]:
        """执行工作流。

        目前没有引入会话级 Memory，因此 `session_id` 先保留为兼容参数。
        """

        graph = await self._get_graph()
        return await graph.ainvoke(initial_state)


_agent_runner: NewsQaAgentRunner | None = None


def get_agent_runner() -> NewsQaAgentRunner:
    """返回全局唯一的 Agent Runner。"""
    global _agent_runner
    if _agent_runner is None:
        _agent_runner = NewsQaAgentRunner()
    return _agent_runner


app = get_agent_runner()
