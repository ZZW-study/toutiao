# -*- coding: utf-8 -*-
"""接口层通用数据模型。

本模块定义多个接口共用的基础响应模型，避免重复定义相同字段。
Pydantic 模型用于：
- 请求数据校验：自动验证字段类型、长度等约束
- 响应数据序列化：统一输出格式，支持别名转换
"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class NewsItemBase(BaseModel):
    """新闻响应基础字段。

    多个接口（收藏列表、浏览历史、新闻列表）共用的新闻数据结构。
    使用 Field alias 实现驼峰命名转换（Python snake_case -> JS camelCase）。
    """

    id: int
    title: str
    description: Optional[str] = None
    image: Optional[str] = None
    author: Optional[str] = None
    category_id: int = Field(alias="categoryId")  # 输出时转为 camelCase
    views: int
    publish_time: Optional[datetime] = Field(None, alias="publishedTime")

    model_config = ConfigDict(
        from_attributes=True,  # 允许从 ORM 模型创建
        populate_by_name=True,  # 允许通过字段名或别名赋值
    )
