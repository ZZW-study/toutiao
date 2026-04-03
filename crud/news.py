#封装实现对新闻table的增删查改操作
from fastapi.encoders import jsonable_encoder
from sqlalchemy import select,func,update
from sqlalchemy.ext.asyncio import AsyncSession,AsyncResult

from models.news import Category,News
from cache.multi_level_cache import multi_level_cache,multi_cache
from cache.redis_cache import cache


@multi_cache(key_prefix="news:categories",expire=7200,hot=True)
async def get_categories(db: AsyncSession,skip: int = 0,limit: int = 100):
    """
    缓存规则：
    key = news:categories:skip=0:limit=100
    热点数据：开启逻辑过期，永久缓存+后台异步更新
    """
    stmt = select(Category).offset(skip).limit(limit)
    result = await db.execute(stmt)
    categories = result.scalars().all()
    return jsonable_encoder(categories) if categories else []


@multi_cache(key_prefix="news:list", expire=1800)
async def get_news_list(db: AsyncSession,category_id: int,skip: int = 0,limit: int = 10):
    """
    缓存规则：
    key = news:list:category_id=1:skip=0:limit=10
    自动分页缓存，L1+L2两级防护
    """
    stmt = select(News).where(News.category_id == category_id).offset(skip).limit(limit)
    result = await db.execute(stmt)
    news_list = result.scalars().all()
    return jsonable_encoder(news_list) if news_list else []


@cache(key_prefix="news:count", expire=300)
async def get_news_count(db:AsyncSession,category_id: int):
    stmt = select(func.count(News.id)).where(News.category_id == category_id)
    result = await db.execute(stmt)
    return result.scalar_one()


async def get_news_detail(db: AsyncSession,news_id: int):
    detail_cache_key = f"news:detail:{news_id}"
    views_cache_key = f"news:views:{news_id}"

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

    async def db_query_views():
        stmt = select(News.views).where(News.id == news_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none() or 0

    current_views = await multi_level_cache.get(views_cache_key, db_query_views)
    news_data["views"] = current_views

    return news_data


async def increase_news_views(db: AsyncSession,news_id: int):
    views_cache_key = f"news:views:{news_id}"

    stmt = update(News).where(News.id == news_id).values(views=News.views + 1)
    result: AsyncResult = await db.execute(stmt)
    await db.commit()
    success = result.rowcount > 0

    if success:
        async def db_query_new_views():
            stmt = select(News.views).where(News.id == news_id)
            result = await db.execute(stmt)
            return result.scalar_one_or_none() or 0

        new_views = await db_query_new_views()
        await multi_level_cache.refresh(views_cache_key, new_views, ttl=86400)

        detail_cache_key = f"news:detail:{news_id}"
        await multi_level_cache.delete(detail_cache_key)

    return success


@multi_cache(key_prefix="news:related",expire=1800)
async def get_related_news(db: AsyncSession,news_id: int,category_id: int,limit: int = 5):
    stmt = select(News).where(News.id != news_id,News.category_id == category_id) \
    .order_by(News.views.desc(),News.publish_time.desc()).limit(limit)
    result = await db.execute(stmt)
    related_news = result.scalars().all()

    return [
         {
              "id": news_detail.id,
              "title": news_detail.title,
              "content": news_detail.content,
              "image": news_detail.image,
              "author": news_detail.author,
              "publishTime": news_detail.publish_time,
              "categoryId": news_detail.category_id,
              "views": news_detail.views,
         }
         for news_detail in related_news
    ]