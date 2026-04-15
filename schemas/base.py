"""接口层通用数据模型。"""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, ConfigDict, Field


class NewsItemBase(BaseModel):
    """新闻响应基础字段。

    这个模型不是数据库表，而是接口对外返回的数据结构。
    它的作用是把多个接口都会用到的新闻字段抽成公共父类，减少重复定义。
    """

    id: int
    title: str
    description: Optional[str] = None
    image: Optional[str] = None
    author: Optional[str] = None
    category_id: int = Field(alias="categoryId")
    views: int
    publish_time: Optional[datetime] = Field(None, alias="publishedTime")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )
