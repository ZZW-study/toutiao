# -*- coding: utf-8 -*-
"""
Agent 工具模块

包含 Agent 节点使用的各种工具：
- news_retriever: 新闻检索工具，整合向量检索和数据库查询
"""

from agents.tools.news_retriever import search_news

__all__ = ["search_news"]
