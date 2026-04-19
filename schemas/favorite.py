# -*- coding: utf-8 -*-
"""收藏模块的请求与响应模型。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from schemas.base import NewsItemBase


class FavoriteAddRequest(BaseModel):
    """添加收藏请求体。"""

    news_id: int = Field(..., alias="newsId")


class FavoriteCheckResponse(BaseModel):
    """检查是否已收藏的响应体。"""

    is_favorite: bool = Field(..., alias="isFavorite")


class FavoriteNewsItemResponse(NewsItemBase):
    """收藏列表中的新闻项，继承基础字段并补充收藏信息。"""

    favorite_id: int = Field(alias="favoriteId")
    favorite_time: datetime = Field(alias="favoriteTime")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )


class FavoriteListResponse(BaseModel):
    """收藏列表响应体。"""

    list: list[FavoriteNewsItemResponse]
    total: int
    has_more: bool = Field(alias="hasMore")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )
