# -*- coding: utf-8 -*-
"""API 路由层统一导出。

本模块统一导出所有路由器，便于在 main.py 中注册。
"""

from routers.users import router as users_router
from routers.news import router as news_router
from routers.favorite import router as favorite_router
from routers.history import router as history_router
from routers.chat import router as chat_router

__all__ = [
    "users_router",
    "news_router",
    "favorite_router",
    "history_router",
    "chat_router",
]
