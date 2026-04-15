"""收藏模块的请求与响应模型。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from schemas.base import NewsItemBase


class FavoriteAddRequest(BaseModel):
    """添加收藏时的请求体。"""

    news_id: int = Field(..., alias="newsId")


class FavoriteCheckResponse(BaseModel):
    """检查某篇新闻是否已收藏时的响应体。"""

    is_favorite: bool = Field(..., alias="isFavorite")


class FavoriteNewsItemResponse(NewsItemBase):
    """收藏列表中的单条新闻数据。

    它在基础新闻字段之上，又补充了“收藏记录本身”的信息，
    例如收藏 ID 和收藏时间。
    """

    favorite_id: int = Field(alias="favoriteId")
    favorite_time: datetime = Field(alias="favoriteTime")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )


class FavoriteListResponse(BaseModel):
    """收藏列表接口响应体。"""

    list: list[FavoriteNewsItemResponse]
    total: int
    has_more: bool = Field(alias="hasMore")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )
