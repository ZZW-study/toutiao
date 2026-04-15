# -*- coding: utf-8 -*-
"""
Agent 工具模块

包含 Agent 节点使用的各种工具：
- news_retriever: 新闻检索工具，整合向量检索和数据库查询
"""

from agents.tools.news_retriever import search_news  # 从 agents.tools.news_retriever 模块导入当前文件后续要用到的对象

__all__ = ["search_news"]  # 把右边计算出来的结果保存到 __all__ 变量中，方便后面的代码继续复用
