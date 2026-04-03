# -*- coding: utf-8 -*-
"""
Agent 状态定义

定义了 LangGraph 工作流中各个节点之间传递的状态数据结构。
状态在整个工作流中流转，每个节点可以读取和修改状态中的字段。
"""

from typing import TypedDict, Optional


class AgentState(TypedDict):
    """
    Agent 状态类

    该状态在整个 LangGraph 工作流中流转，记录用户问题、检索过程和最终答案。

    属性:
        query: 用户原始问题，例如 "华为最近有什么新闻？"
        keywords: 从问题中提取的关键词列表，用于优化检索
        category: 识别出的新闻类别（科技/财经/国际等），可能为空
        search_query: 实际用于检索的查询语句，由关键词组合而成
        news_list: 检索到的相关新闻列表，每条新闻包含 id、title、content 等字段
        answer: 最终生成的回答文本
        loop_count: 当前循环次数，用于限制最大重试次数
        is_satisfied: 回答是否充分，用于判断是否需要继续循环
    """
    # 用户输入的原始问题
    query: str

    # 从问题中提取的关键词列表
    keywords: list[str]

    # 识别出的新闻类别（可选）
    # 可能的值：科技、财经、国际、体育、娱乐、社会、国内、头条
    category: Optional[str]

    # 用于检索的查询字符串
    # 由关键词组合而成，循环重试时会扩展
    search_query: str

    # 检索到的新闻列表
    # 每条新闻是一个字典，包含 id、title、content、category_id 等字段
    news_list: list[dict]

    # 生成的回答文本
    answer: str

    # 当前循环次数（初始为0，每次循环+1）
    loop_count: int

    # 回答是否充分
    # True: 回答已经足够好，可以结束
    # False: 回答不充分，需要重新检索
    is_satisfied: bool
