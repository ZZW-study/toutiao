# -*- coding: utf-8 -*-
"""收藏相关的 CRUD 操作。

提供收藏的增删查功能，并维护缓存一致性。
"""

from sqlalchemy import func, select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from models.news import News
from models.favorite import Favorite
from cache.multi_level_cache import multi_level_cache


async def is_news_favorite(db: AsyncSession, user_id: int, news_id: int) -> bool:
    """检查用户是否已收藏指定新闻。"""
    query = select(Favorite).where(Favorite.user_id == user_id, Favorite.news_id == news_id)
    result = await db.execute(query)
    return result.scalar_one_or_none() is not None


async def add_news_favorite(db: AsyncSession, user_id: int, news_id: int):
    """添加收藏，成功后失效相关缓存。"""
    favorite = Favorite(user_id=user_id, news_id=news_id)
    db.add(favorite)
    await db.commit()
    await db.refresh(favorite)

    # 失效缓存
    await multi_level_cache.delete(f"favorite:check:{user_id}:{news_id}")
    await multi_level_cache.delete(f"favorite:list:{user_id}")

    return favorite


async def remove_news_favorite(db: AsyncSession, user_id: int, news_id: int) -> bool:
    """移除收藏，返回是否删除成功。"""
    stmt = delete(Favorite).where(Favorite.user_id == user_id, Favorite.news_id == news_id)
    result = await db.execute(stmt)
    await db.commit()

    # 失效缓存
    await multi_level_cache.delete(f"favorite:check:{user_id}:{news_id}")
    await multi_level_cache.delete(f"favorite:list:{user_id}")

    return result.rowcount > 0


async def get_favorite_list(db: AsyncSession, user_id: int, page: int = 1, page_size: int = 10):
    """分页查询用户收藏列表，返回 (rows, total)。"""
    count_query = select(func.count()).where(Favorite.user_id == user_id)
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    query = (
        select(
            News,
            Favorite.created_at.label("favorite_time"),
            Favorite.id.label("favorite_id"),
        )
        .join(Favorite, Favorite.news_id == News.id)
        .where(Favorite.user_id == user_id)
        .order_by(Favorite.created_at.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(query)
    rows = result.all()

    return rows, total


async def remove_all_favorites(db: AsyncSession, user_id: int):
    """删除用户所有收藏，返回删除数量。"""
    stmt = delete(Favorite).where(Favorite.user_id == user_id)
    result = await db.execute(stmt)
    await db.commit()

    await multi_level_cache.delete(f"favorite:list:{user_id}")

    return result.rowcount or 0
