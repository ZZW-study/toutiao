# -*- coding: utf-8 -*-
"""Pydantic 数据模型统一导出。

本模块统一导出所有请求/响应模型。
"""

from schemas.base import NewsItemBase
from schemas.users import (
    UserRequest,
    UserUpdateRequest,
    UserChangePasswordRequest,
    UserInfoBase,
    UserInfoResponse,
    UserAuthResponse,
)
from schemas.favorite import (
    FavoriteAddRequest,
    FavoriteCheckResponse,
    FavoriteNewsItemResponse,
    FavoriteListResponse,
)
from schemas.history import (
    ViewHistoryAddRequest,
    ViewHistoryResponse,
    ViewHistory,
    ViewHistoryListResponse,
)
from schemas.chat import ChatRequest, ChatResponse, NewsItem

__all__ = [
    # 基础模型
    "NewsItemBase",
    # 用户模型
    "UserRequest",
    "UserUpdateRequest",
    "UserChangePasswordRequest",
    "UserInfoBase",
    "UserInfoResponse",
    "UserAuthResponse",
    # 收藏模型
    "FavoriteAddRequest",
    "FavoriteCheckResponse",
    "FavoriteNewsItemResponse",
    "FavoriteListResponse",
    # 历史模型
    "ViewHistoryAddRequest",
    "ViewHistoryResponse",
    "ViewHistory",
    "ViewHistoryListResponse",
    # 聊天模型
    "ChatRequest",
    "ChatResponse",
    "NewsItem",
]
