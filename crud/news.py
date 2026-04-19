# -*- coding: utf-8 -*-
"""新闻数据访问层。

提供新闻分类、列表、详情、浏览量和相关推荐等数据库访问逻辑。
使用多级缓存减少数据库压力。
"""

from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncResult, AsyncSession

from cache.multi_level_cache import multi_cache, multi_level_cache
from cache.redis_cache import cache
from models.news import Category, News


# ---- 分类与列表查询 ----

@multi_cache(key_prefix="news:categories", expire=7200, hot=True)
async def get_categories(db: AsyncSession, skip: int = 0, limit: int = 100):
    """读取新闻分类列表，使用热点缓存。"""
    stmt = select(Category).offset(skip).limit(limit)
    result = await db.execute(stmt)
    categories = result.scalars().all()
    return jsonable_encoder(categories) if categories else []


@multi_cache(key_prefix="news:list", expire=1800)
async def get_news_list(
    db: AsyncSession,
    category_id: int,
    skip: int = 0,
    limit: int = 10,
):
    """按分类读取新闻列表并缓存。"""
    stmt = (
        select(News)
        .where(News.category_id == category_id)
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    news_list = result.scalars().all()
    return jsonable_encoder(news_list) if news_list else []


@cache(key_prefix="news:count", expire=300)
async def get_news_count(db: AsyncSession, category_id: int):
    """获取指定分类下的新闻总数。"""
    stmt = select(func.count(News.id)).where(News.category_id == category_id)
    result = await db.execute(stmt)
    return result.scalar_one()


# ---- 新闻详情与浏览量 ----

async def get_news_detail(db: AsyncSession, news_id: int):
    """获取新闻详情，详情主体和浏览量分开缓存。

    详情字段几乎不变，浏览量高频更新，分开缓存避免频繁重建。
    """
    detail_cache_key = f"news:detail:{news_id}"
    views_cache_key = f"news:views:{news_id}"

    # 查询详情主体
    async def db_query_detail():
        stmt = select(News).where(News.id == news_id)
        result = await db.execute(stmt)
        news = result.scalar_one_or_none()
        if not news:
            return None
        return {
            "id": news.id,
            "title": news.title,
            "content": news.content,
            "image": news.image,
            "author": news.author,
            "publish_time": news.publish_time,
            "category_id": news.category_id,
        }

    news_data = await multi_level_cache.get(detail_cache_key, db_query_detail)
    if not news_data:
        return None

    # 单独查询浏览量
    async def db_query_views():
        stmt = select(News.views).where(News.id == news_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none() or 0

    current_views = await multi_level_cache.get(views_cache_key, db_query_views)
    news_data["views"] = current_views
    return news_data


async def increase_news_views(db: AsyncSession, news_id: int):
    """原子自增新闻浏览量，并同步刷新缓存。"""
    views_cache_key = f"news:views:{news_id}"

    # 先更新数据库
    stmt = update(News).where(News.id == news_id).values(views=News.views + 1)
    result: AsyncResult = await db.execute(stmt)
    await db.commit()
    success = result.rowcount > 0

    if success:
        # 读取最新浏览量并刷新缓存
        async def db_query_new_views():
            stmt = select(News.views).where(News.id == news_id)
            result = await db.execute(stmt)
            return result.scalar_one_or_none() or 0

        new_views = await db_query_new_views()
        await multi_level_cache.refresh(views_cache_key, new_views, ttl=86400)

        detail_cache_key = f"news:detail:{news_id}"
        await multi_level_cache.delete(detail_cache_key)

    return success


# ---- 相关推荐 ----

@multi_cache(key_prefix="news:related", expire=1800)
async def get_related_news(
    db: AsyncSession,
    news_id: int,
    category_id: int,
    limit: int = 5,
):
    """获取同分类相关推荐，按浏览量和发布时间排序。"""
    stmt = (
        select(News)
        .where(News.id != news_id, News.category_id == category_id)
        .order_by(News.views.desc(), News.publish_time.desc())
        .limit(limit)
    )
    result = await db.execute(stmt)
    related_news = result.scalars().all()

    return [
        {
            "id": item.id,
            "title": item.title,
            "content": item.content,
            "image": item.image,
            "author": item.author,
            "publishTime": item.publish_time,
            "categoryId": item.category_id,
            "views": item.views,
        }
        for item in related_news
    ]
