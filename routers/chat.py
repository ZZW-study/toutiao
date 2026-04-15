# -*- coding: utf-8 -*-
"""智能问答路由。"""

from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from agents.graph import get_agent_runner
from middlewares.token_bucket_rate_limit import rate_limit_dependency
from rag.vectorstore import get_vectorstore_stats
from schemas.chat import ChatRequest, ChatResponse, NewsItem
from utils.logger import get_logger

logger = get_logger(name="ChatRouter")

router = APIRouter(
    prefix="/chat",
    tags=["智能问答"],
    dependencies=[Depends(rate_limit_dependency)],
)


def _build_initial_state(query: str) -> dict:
    """构造 Agent 初始状态。"""

    return {
        "query": query,
        "keywords": [],
        "category": None,
        "search_query": "",
        "news_list": [],
        "answer": "",
        "loop_count": 0,
        "is_satisfied": False,
    }


@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    """执行新闻问答。"""

    logger.info("收到聊天请求", query_preview=request.query[:50])

    try:
        result = await get_agent_runner().ainvoke(_build_initial_state(request.query))
    except Exception as exc:
        logger.error("聊天请求处理失败", error=str(exc), exc_info=True)
        raise HTTPException(status_code=500, detail=f"处理请求失败: {exc}") from exc

    news_list = [
        NewsItem(
            id=int(news.get("id", 0)),
            title=str(news.get("title", "")),
            content=str(news.get("content", "")),
            description=news.get("description"),
            category_id=int(news.get("category_id", 0)),
            publish_time=news.get("publish_time"),
            image=news.get("image"),
            author=news.get("author"),
        )
        for news in result.get("news_list", [])
    ]

    return ChatResponse(
        answer=result.get("answer", "抱歉，暂时无法生成回答。"),
        news_list=news_list,
        loop_count=result.get("loop_count", 0),
    )


@router.get("/stats")
async def get_stats() -> dict:
    """查看向量库状态。"""

    stats = get_vectorstore_stats()
    return {
        "status": "ok",
        "vector_count": stats["total_vectors"],
        "persist_directory": stats["persist_directory"],
    }


@router.post("/index")
async def trigger_index() -> dict:
    """手动触发全量索引。"""

    from indexer import index_all_news

    logger.info("收到手动全量索引请求")
    result = await index_all_news()
    return {
        "status": "ok",
        "result": result,
    }

