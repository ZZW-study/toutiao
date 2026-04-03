# -*- coding: utf-8 -*-
"""
新闻问答 API 接口

该模块提供智能对话的 REST API 接口，允许用户通过 HTTP 请求与新闻问答 Agent 交互。

API 端点：
- POST /chat/ : 发送问题，获取回答

使用方法：
    请求：
    POST /chat/
    Content-Type: application/json
    {
        "query": "华为最近有什么新闻？"
    }

    响应：
    {
        "answer": "根据最近的新闻，华为发布了...",
        "news_list": [
            {"id": 1, "title": "...", "content": "..."},
            ...
        ]
    }
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional, List

from agents.graph import app as agent_app
from utils.logger import get_logger

# 获取日志记录器
logger = get_logger(name="ChatRouter")


# ========== 创建路由器 ==========
router = APIRouter(prefix="/chat", tags=["智能问答"])


# ========== 请求/响应模型 ==========
class ChatRequest(BaseModel):
    """
    对话请求模型

    属性:
        query: 用户的问题，必填，最大长度 500 字符
    """
    query: str = Field(
        ...,
        max_length=500,
        description="用户问题",
        examples=["华为最近有什么新闻？"]
    )


class NewsItem(BaseModel):
    """
    新闻项模型

    用于在响应中返回相关新闻的信息
    """
    id: int = Field(description="新闻 ID")
    title: str = Field(description="新闻标题")
    content: str = Field(description="新闻内容")
    description: Optional[str] = Field(default=None, description="新闻简介")
    category_id: int = Field(description="类别 ID")
    publish_time: Optional[str] = Field(default=None, description="发布时间")
    image: Optional[str] = Field(default=None, description="封面图片 URL")
    author: Optional[str] = Field(default=None, description="作者")


class ChatResponse(BaseModel):
    """
    对话响应模型

    属性:
        answer: Agent 生成的回答
        news_list: 引用的新闻列表
        loop_count: 循环次数（用于调试）
    """
    answer: str = Field(description="回答内容")
    news_list: List[NewsItem] = Field(
        default_factory=list,
        description="相关新闻列表"
    )
    loop_count: int = Field(
        default=0,
        description="循环次数"
    )


# ========== API 端点 ==========
@router.post("/", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    智能对话接口

    接收用户问题，调用 LangGraph Agent 进行处理，返回回答。

    处理流程：
    1. 问题分析：提取关键词，识别类别
    2. 新闻检索：从向量库和数据库检索相关新闻
    3. 回答生成：基于新闻内容生成回答
    4. 循环检查：如果回答不充分，重新检索

    参数:
        request: ChatRequest，包含用户问题

    返回:
        ChatResponse，包含回答和相关新闻

    异常:
        HTTPException: 处理失败时返回 500 错误
    """
    logger.info(f"收到对话请求: {request.query[:50]}...")

    try:
        # ========== 调用 Agent ==========
        # 构建初始状态
        initial_state = {
            "query": request.query,
            "keywords": [],
            "category": None,
            "search_query": "",
            "news_list": [],
            "answer": "",
            "loop_count": 0,
            "is_satisfied": False
        }

        # 异步调用 LangGraph 工作流
        result = await agent_app.ainvoke(initial_state)

        # ========== 构建响应 ==========
        # 提取相关新闻列表
        news_list = []
        for news in result.get("news_list", []):
            news_list.append(NewsItem(
                id=news.get("id", 0),
                title=news.get("title", ""),
                content=news.get("content", ""),
                description=news.get("description"),
                category_id=news.get("category_id", 0),
                publish_time=news.get("publish_time"),
                image=news.get("image"),
                author=news.get("author")
            ))

        response = ChatResponse(
            answer=result.get("answer", "抱歉，无法生成回答。"),
            news_list=news_list,
            loop_count=result.get("loop_count", 0)
        )

        logger.info(f"对话完成 - 回答长度: {len(response.answer)}, 引用新闻: {len(news_list)}, 循环次数: {response.loop_count}")

        return response

    except Exception as e:
        # 异常处理
        logger.error(f"处理对话请求失败: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"处理请求失败: {str(e)}"
        )


@router.get("/stats")
async def get_stats():
    """
    获取 Agent 统计信息

    返回向量库的状态信息，用于监控和调试。

    返回:
        包含向量数量的字典
    """
    from rag.vectorstore import get_vectorstore_stats

    stats = get_vectorstore_stats()

    return {
        "status": "ok",
        "vector_count": stats["total_vectors"],
        "persist_directory": stats["persist_directory"]
    }


@router.post("/index")
async def trigger_index():
    """
    触发全量索引

    手动触发新闻索引构建。
    通常用于系统初始化或数据修复。

    返回:
        索引结果
    """
    from rag.indexer import index_all_news

    logger.info("手动触发全量索引")

    result = await index_all_news()

    return {
        "status": "ok",
        "result": result
    }
