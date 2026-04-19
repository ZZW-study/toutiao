"""数据库模型统一导出。

便于：1. 统一管理模型导入  2. 数据库迁移工具扫描所有模型  3. 模型间依赖关系正确处理
"""

from models.base import Base, TimestampMixin
from models.users import User, UserToken
from models.news import News, Category
from models.favorite import Favorite
from models.history import ViewHistory

__all__ = [
    "Base",
    "TimestampMixin",
    "User",
    "UserToken",
    "News",
    "Category",
    "Favorite",
    "ViewHistory",
]
