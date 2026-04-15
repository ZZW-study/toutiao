# -*- coding: utf-8 -*-
"""新闻检索服务。

职责拆分：
- 向量库只负责语义召回。
- 本服务负责把召回结果补全成结构化新闻数据。
- 路由与 Agent 只消费最终结果，不再关心底层检索细节。
"""

from __future__ import annotations

from typing import Any, Optional

from sqlalchemy import select

from configs.db_conf import AsyncSessionLocal
from models.news import News
from rag.vectorstore import VectorStoreService, get_vectorstore_service
from utils.logger import get_logger

logger = get_logger(name="NewsRetriever")

CATEGORY_ID_MAP = {
    "头条": 1,
    "社会": 2,
    "国内": 3,
    "国际": 4,
    "娱乐": 5,
    "体育": 6,
    "科技": 7,
    "财经": 8,
}


def _serialize_news(news: News) -> dict[str, Any]:
    """统一新闻输出格式。"""

    return {
        "id": news.id,
        "title": news.title,
        "content": news.content,
        "description": news.description,
        "category_id": news.category_id,
        "publish_time": news.publish_time.isoformat() if news.publish_time else None,
        "image": news.image,
        "author": news.author,
    }


class NewsRetrieverService:
    """组合向量检索与数据库补全的服务层。"""

    def __init__(
        self,
        vectorstore_service: Optional[VectorStoreService] = None,
    ) -> None:
        """初始化检索服务，可按需注入向量库依赖。"""
        self.vectorstore_service = vectorstore_service or get_vectorstore_service()

    async def search_news(
        self,
        query: str,
        category: Optional[str] = None,
        top_k: int = 5,
    ) -> list[dict[str, Any]]:
        """优先走语义检索，再用数据库补齐详情。"""

        query = (query or "").strip()
        if not query:
            return []

        category_id = CATEGORY_ID_MAP.get(category) if category else None
        logger.info("开始检索新闻", query=query, category=category, top_k=top_k)

        docs = await self.vectorstore_service.asearch(
            query=query,
            top_k=max(top_k * 2, top_k),
            category_id=category_id,
        )

        news_ids: list[int] = []
        seen_ids: set[int] = set()
        for doc in docs:
            raw_news_id = doc.metadata.get("news_id")
            if raw_news_id is None:
                continue
            try:
                news_id = int(raw_news_id)
            except (TypeError, ValueError):
                continue
            if news_id in seen_ids:
                continue
            seen_ids.add(news_id)
            news_ids.append(news_id)

        if not news_ids and category_id is not None:
            # 当向量召回为空时，按分类走一个结构化兜底，避免问“科技新闻”却直接返回空。
            return await self.search_news_by_category(category=category, limit=top_k)

        if not news_ids:
            return []

        async with AsyncSessionLocal() as db:
            result = await db.execute(select(News).where(News.id.in_(news_ids)))
            news_list = result.scalars().all()

        news_map = {news.id: news for news in news_list}
        results = [_serialize_news(news_map[news_id]) for news_id in news_ids if news_id in news_map]
        return results[:top_k]

    async def search_news_by_category(
        self,
        category: str,
        limit: int = 10,
    ) -> list[dict[str, Any]]:
        """按分类直接查询数据库。"""

        category_id = CATEGORY_ID_MAP.get(category)
        if category_id is None:
            return []

        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(News)
                .where(News.category_id == category_id)
                .order_by(News.publish_time.desc(), News.id.desc())
                .limit(limit)
            )
            rows = result.scalars().all()

        return [_serialize_news(news) for news in rows]


_news_retriever_service: Optional[NewsRetrieverService] = None


def get_news_retriever_service() -> NewsRetrieverService:
    """返回新闻检索服务的全局单例。"""
    global _news_retriever_service
    if _news_retriever_service is None:
        _news_retriever_service = NewsRetrieverService()
    return _news_retriever_service


async def search_news(
    query: str,
    category: Optional[str] = None,
    top_k: int = 5,
) -> list[dict[str, Any]]:
    """兼容旧接口。"""

    return await get_news_retriever_service().search_news(query=query, category=category, top_k=top_k)


async def search_news_by_category(
    category: str,
    limit: int = 10,
) -> list[dict[str, Any]]:
    """兼容旧接口，按分类直接查询新闻。"""
    return await get_news_retriever_service().search_news_by_category(category=category, limit=limit)
