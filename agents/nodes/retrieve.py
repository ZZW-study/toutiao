# -*- coding: utf-8 -*-
"""
新闻检索节点

该节点负责从向量库和数据库中检索相关新闻，完成以下任务：
1. 向量检索：使用语义相似度在向量库中检索相关新闻
2. 数据库补充：从 MySQL 数据库获取新闻的完整信息
3. 类别过滤：根据识别的类别对结果进行过滤（可选）

检索策略：
- 首先通过向量相似度检索获取候选新闻
- 然后从数据库获取完整的新闻内容
- 最后根据类别进行过滤（如果指定了类别）
"""

from typing import Dict, Any

from agents.state import AgentState
from agents.tools.news_retriever import search_news
from utils.logger import get_logger

# 获取日志记录器
logger = get_logger(name="RetrieveNode")


async def retrieve_node(state: AgentState) -> Dict[str, Any]:
    """
    新闻检索节点的主函数

    该函数被 LangGraph 调用，执行新闻检索逻辑：
    1. 获取检索查询字符串和类别（来自 analyze 节点）
    2. 调用检索工具获取相关新闻
    3. 将检索结果存入状态

    参数:
        state: 当前 Agent 状态，包含 search_query、category 等字段

    返回:
        状态更新字典，包含以下字段：
        - news_list: 检索到的新闻列表
    """
    # 获取检索查询字符串
    search_query = state.get("search_query", "")

    # 获取类别过滤条件（可能为 None）
    category = state.get("category")

    # 获取循环次数，用于决定检索数量
    loop_count = state.get("loop_count", 1)

    logger.info(f"开始检索新闻 - 查询: '{search_query}', 类别: {category}")

    # ========== 动态调整检索数量 ==========
    # 如果是重试，增加检索数量以获取更多候选
    top_k = 5 + (loop_count - 1) * 2  # 第一次5条，第二次7条，第三次9条
    top_k = min(top_k, 15)  # 最多15条

    try:
        # ========== 调用检索工具 ==========
        # 检索工具负责向量检索和数据库查询
        news_list = await search_news(
            query=search_query,
            category=category,
            top_k=top_k
        )

        logger.info(f"检索完成，获取到 {len(news_list)} 条新闻")

        # 打印检索到的新闻标题（用于调试）
        for i, news in enumerate(news_list[:3]):
            logger.debug(f"  [{i+1}] {news.get('title', 'N/A')}")

    except Exception as e:
        # 检索失败，记录错误并返回空列表
        logger.error(f"检索新闻失败: {e}")
        news_list = []

    # ========== 返回状态更新 ==========
    return {
        "news_list": news_list
    }
