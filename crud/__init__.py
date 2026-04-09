# -*- coding: utf-8 -*-
"""CRUD 数据访问层统一导出。

本模块统一导出所有 CRUD 操作模块。
"""

from crud.users import get_user_by_username, create_user, get_user_by_id
from crud.news import get_news_list, get_news_detail, get_categories
from crud.favorite import add_favorite, remove_favorite, get_favorite_list
from crud.history import add_view_history, get_view_history_list

__all__ = [
    "get_user_by_username",
    "create_user",
    "get_user_by_id",
    "get_news_list",
    "get_news_detail",
    "get_categories",
    "add_favorite",
    "remove_favorite",
    "get_favorite_list",
    "add_view_history",
    "get_view_history_list",
]
