# -*- coding: utf-8 -*-
"""
新闻检索工具

该工具整合向量检索和数据库查询，为 Agent 提统一的新闻检索接口。

检索流程：
1. 向量检索：在 Chroma 向量库中进行语义相似度检索
2. 数据库补充：根据向量检索结果，从 MySQL 获取完整新闻信息
3. 类别过滤：根据类别对结果进行过滤（可选）

这种混合检索策略兼顾了语义理解和结构化数据的优势。
"""

from typing import Optional, List, Dict

from sqlalchemy import select

from configs.db_conf import AsyncSessionLocal
from models.news import News
from utils.logger import get_logger

# 获取日志记录器
logger = get_logger(name="NewsRetriever")


# ========== 类别名称到 ID 的映射 ==========
# 用于将中文类别名称转换为数据库中的 category_id
CATEGORY_ID_MAP = {
    "头条": 1,
    "社会": 2,
    "国内": 3,
    "国际": 4,
    "娱乐": 5,
    "体育": 6,
    "科技": 7,
    "财经": 8
}


async def search_news(
    query: str,
    category: Optional[str] = None,
    top_k: int = 5
) -> List[Dict]:
    """
    搜索新闻的主函数

    整合向量检索和数据库查询，返回结构化的新闻列表。

    参数:
        query: 检索查询字符串，可以是关键词或自然语言描述
        category: 类别过滤条件（可选），如 "科技"、"财经" 等
        top_k: 返回的最大新闻数量

    返回:
        新闻列表，每条新闻是一个字典，包含以下字段：
        - id: 新闻 ID
        - title: 新闻标题
        - content: 新闻内容
        - description: 新闻简介
        - category_id: 类别 ID
        - publish_time: 发布时间
        - image: 封面图片 URL（可选）
        - author: 作者（可选）
    """
    logger.info(f"开始搜索新闻 - 查询: '{query}', 类别: {category}, top_k: {top_k}")

    results = []

    try:
        # ========== 第一步：向量检索 ==========
        # 从向量库中检索语义相似的新闻
        # 这里会延迟导入，避免循环依赖
        from rag.vectorstore import get_vectorstore

        vectorstore = get_vectorstore()

        # 执行向量相似度检索
        # 返回 top_k * 2 条结果，为后续过滤留出余量
        docs = vectorstore.similarity_search(query, k=top_k * 2)

        logger.debug(f"向量检索返回 {len(docs)} 条结果")

        # 提取向量库中的新闻 ID 列表
        news_ids = []
        for doc in docs:
            news_id = doc.metadata.get("news_id")
            if news_id:
                news_ids.append(news_id)

        # ========== 第二步：数据库查询 ==========
        # 根据向量检索结果，从数据库获取完整新闻信息
        if news_ids:
            async with AsyncSessionLocal() as db:
                # 查询新闻表
                stmt = select(News).where(News.id.in_(news_ids))
                result = await db.execute(stmt)
                news_list = result.scalars().all()

                # 构建 ID 到新闻对象的映射，保持向量检索的顺序
                news_map = {news.id: news for news in news_list}

                # 按向量检索顺序整理结果
                for news_id in news_ids:
                    if news_id in news_map:
                        news = news_map[news_id]
                        results.append({
                            "id": news.id,
                            "title": news.title,
                            "content": news.content,
                            "description": news.description,
                            "category_id": news.category_id,
                            "publish_time": news.publish_time.isoformat() if news.publish_time else None,
                            "image": news.image,
                            "author": news.author
                        })

        logger.info(f"数据库查询返回 {len(results)} 条新闻")

        # ========== 第三步：类别过滤 ==========
        # 如果指定了类别，过滤结果
        if category and category in CATEGORY_ID_MAP:
            category_id = CATEGORY_ID_MAP[category]
            results = [r for r in results if r["category_id"] == category_id]
            logger.info(f"类别过滤后剩余 {len(results)} 条新闻")

        # ========== 第四步：截断结果 ==========
        # 确保返回数量不超过 top_k
        results = results[:top_k]

    except Exception as e:
        logger.error(f"搜索新闻失败: {e}")
        # 返回空列表而不是抛出异常，避免中断工作流
        results = []

    return results


async def search_news_by_category(
    category: str,
    limit: int = 10
) -> List[Dict]:
    """
    按类别搜索新闻

    这是一个便捷函数，直接从数据库按类别查询新闻，
    不使用向量检索。适用于用户明确指定类别的情况。

    参数:
        category: 类别名称，如 "科技"、"财经" 等
        limit: 返回的最大数量

    返回:
        新闻列表，格式同 search_news
    """
    if category not in CATEGORY_ID_MAP:
        logger.warning(f"无效的类别: {category}")
        return []

    category_id = CATEGORY_ID_MAP[category]
    results = []

    try:
        async with AsyncSessionLocal() as db:
            # 按类别查询，按发布时间倒序
            stmt = (
                select(News)
                .where(News.category_id == category_id)
                .order_by(News.publish_time.desc())
                .limit(limit)
            )
            result = await db.execute(stmt)
            news_list = result.scalars().all()

            for news in news_list:
                results.append({
                    "id": news.id,
                    "title": news.title,
                    "content": news.content,
                    "description": news.description,
                    "category_id": news.category_id,
                    "publish_time": news.publish_time.isoformat() if news.publish_time else None,
                    "image": news.image,
                    "author": news.author
                })

        logger.info(f"按类别 '{category}' 查询到 {len(results)} 条新闻")

    except Exception as e:
        logger.error(f"按类别查询失败: {e}")

    return results
