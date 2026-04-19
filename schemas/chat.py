# -*- coding: utf-8 -*-
"""智能问答相关的 Pydantic 模型定义。

定义 AI 问答接口的请求和响应格式。
"""

from pydantic import BaseModel, Field
from typing import Optional, List


class ChatRequest(BaseModel):
    """对话请求模型。"""

    query: str = Field(
        ...,
        max_length=500,
        description="用户问题",
        examples=["华为最近有什么新闻？"],
    )


class NewsItem(BaseModel):
    """响应中返回的相关新闻信息。"""

    id: int = Field(description="新闻 ID")
    title: str = Field(description="新闻标题")
    content: str = Field(description="新闻内容")
    description: Optional[str] = Field(default=None, description="新闻简介")
    category_id: int = Field(description="类别 ID")
    publish_time: Optional[str] = Field(default=None, description="发布时间")
    image: Optional[str] = Field(default=None, description="封面图片 URL")
    author: Optional[str] = Field(default=None, description="作者")


class ChatResponse(BaseModel):
    """对话响应模型。"""

    answer: str = Field(description="回答内容")
    news_list: List[NewsItem] = Field(
        default_factory=list,
        description="相关新闻列表",
    )
    loop_count: int = Field(
        default=0,
        description="循环次数",
    )
