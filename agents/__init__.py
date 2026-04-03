# -*- coding: utf-8 -*-
"""
新闻问答 Agent 模块

该模块基于 LangGraph 实现多 Agent 编排，用于智能问答新闻相关内容。
主要包含：
- graph.py: LangGraph 编排入口
- state.py: Agent 状态定义
- nodes/: 各个 Agent 节点实现
- tools/: Agent 使用的工具
"""

from agents.graph import app as agent_app

__all__ = ["agent_app"]
