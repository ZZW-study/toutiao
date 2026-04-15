# -*- coding: utf-8 -*-
"""
Agent 节点模块

包含 LangGraph 工作流中的所有节点实现：
- analyze: 问题分析节点，提取关键词和识别类别
- retrieve: 新闻检索节点，从向量库和数据库检索相关新闻
- generate: 回答生成节点，基于检索结果生成回答
"""

from agents.nodes.analyze import analyze_node  # 从 agents.nodes.analyze 模块导入当前文件后续要用到的对象
from agents.nodes.retrieve import retrieve_node  # 从 agents.nodes.retrieve 模块导入当前文件后续要用到的对象
from agents.nodes.generate import generate_node  # 从 agents.nodes.generate 模块导入当前文件后续要用到的对象

__all__ = ["analyze_node", "retrieve_node", "generate_node"]  # 把右边计算出来的结果保存到 __all__ 变量中，方便后面的代码继续复用
