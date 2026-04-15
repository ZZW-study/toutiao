"""浏览历史模块的请求与响应模型。"""

from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field

from schemas.base import NewsItemBase


class ViewHistoryAddRequest(BaseModel):
    """新增一条浏览历史时的请求体。"""

    news_id: int = Field(..., alias="newsId")


class ViewHistoryResponse(BaseModel):
    """单条浏览历史记录的基础响应体。"""

    id: int = Field(...)
    user_id: int = Field(..., alias="userId")
    news_id: int = Field(..., alias="newsId")
    view_time: datetime = Field(..., alias="viewTime")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True,
    )


class ViewHistory(NewsItemBase):
    """浏览历史列表中的单条新闻项。"""

    view_time: datetime = Field(..., alias="viewTime")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )


class ViewHistoryListResponse(BaseModel):
    """浏览历史列表接口响应体。"""

    list: list[ViewHistory]
    total: int = Field(...)
    has_more: bool = Field(..., alias="hasMore")

    model_config = ConfigDict(
        from_attributes=True,
        populate_by_name=True,
    )
