"""收藏（Favorite）相关的 CRUD 操作。

职责：
- 检查某条新闻是否被当前用户收藏
- 添加/删除收藏，并维护缓存一致性
- 查询用户收藏列表（分页）与清空全部收藏
"""

from sqlalchemy import func, select, delete
from sqlalchemy.ext.asyncio import AsyncSession
from models.news import News
from models.favorite import Favorite
from cache.multi_level_cache import multi_level_cache


async def is_news_favorite(db: AsyncSession, user_id: int, news_id: int) -> bool:
    """检查指定用户是否已收藏指定新闻，返回布尔值。"""
    query = select(Favorite).where(Favorite.user_id == user_id, Favorite.news_id == news_id)
    result = await db.execute(query)
    return result.scalar_one_or_none() is not None


async def add_news_favorite(db: AsyncSession, user_id: int, news_id: int):
    """添加收藏并返回新增的 `Favorite` 实例。

    成功后会删除相关缓存（单条检查、收藏列表）以保证一致性。
    """
    favorite = Favorite(user_id=user_id, news_id=news_id)
    db.add(favorite)
    await db.commit()
    await db.refresh(favorite)

    # 删除缓存以便下次读取为最新状态
    await multi_level_cache.delete(f"favorite:check:{user_id}:{news_id}")
    await multi_level_cache.delete(f"favorite:list:{user_id}")

    return favorite


async def remove_news_favorite(db: AsyncSession, user_id: int, news_id: int) -> bool:
    """移除指定用户对指定新闻的收藏，返回是否删除成功。"""
    stmt = delete(Favorite).where(Favorite.user_id == user_id, Favorite.news_id == news_id)
    result = await db.execute(stmt)
    await db.commit()

    # 删除缓存
    await multi_level_cache.delete(f"favorite:check:{user_id}:{news_id}")
    await multi_level_cache.delete(f"favorite:list:{user_id}")

    return result.rowcount > 0


async def get_favorite_list(db: AsyncSession, user_id: int, page: int = 1, page_size: int = 10):
    """分页查询用户的收藏列表，返回 `(rows, total)`。

    rows 中的每一项为 `(News, favorite_time, favorite_id)`。
    """
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
    """删除用户的所有收藏，返回删除的记录数或 0。"""
    stmt = delete(Favorite).where(Favorite.user_id == user_id)
    result = await db.execute(stmt)
    await db.commit()

    await multi_level_cache.delete(f"favorite:list:{user_id}")

    return result.rowcount or 0