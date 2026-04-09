# -*- coding: utf-8 -*-
"""智能问答相关的 Pydantic 模型定义。

包含对话请求和响应的数据模型。
"""


from pydantic import BaseModel, Field
from typing import Optional, List


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
