"""新闻数据访问层。

这个模块负责新闻分类、列表、详情、浏览量和相关推荐等数据库访问逻辑。

为什么单独放在 CRUD 层：
1. 路由层只负责接收请求和组织响应，不直接写 SQL。
2. 缓存策略与数据库访问紧耦合，放在这里最容易保持一致。
3. 后续如果要把某些查询替换成搜索引擎或读库，也只需要改这一层。
"""

from fastapi.encoders import jsonable_encoder
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncResult, AsyncSession

from cache.multi_level_cache import multi_cache, multi_level_cache
from cache.redis_cache import cache
from models.news import Category, News


@multi_cache(key_prefix="news:categories", expire=7200, hot=True)
async def get_categories(db: AsyncSession, skip: int = 0, limit: int = 100):
    """读取新闻分类列表。

    这里使用热点缓存（logic_cache）是因为分类数据非常稳定、变更频率极低，
    很适合走“过期后先返回旧值，后台慢慢重建”的策略。
    """
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
    """按分类读取新闻列表并缓存分页结果。"""
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
    """获取指定分类下的新闻总数。

    总数变动频率比列表数据更高，但仍然不需要每次实时查询，
    短 TTL 缓存即可明显减少分页接口中的 count 压力。
    """
    stmt = select(func.count(News.id)).where(News.category_id == category_id)
    result = await db.execute(stmt)
    return result.scalar_one()


async def get_news_detail(db: AsyncSession, news_id: int):
    """获取单条新闻详情。

    这里把“详情主体”和“浏览量”拆成两个缓存键，有两个原因：
    1. 正文、标题、作者等字段几乎不变。
    2. views 是高频写字段，单独缓存能避免每次阅读都重建完整详情缓存。
    """
    detail_cache_key = f"news:detail:{news_id}"
    views_cache_key = f"news:views:{news_id}"

    async def db_query_detail():
        """查询新闻详情主体字段，供详情缓存未命中时回源使用。"""
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
        """单独查询浏览量字段，避免频繁重建整条详情缓存。"""
        stmt = select(News.views).where(News.id == news_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none() or 0

    current_views = await multi_level_cache.get(views_cache_key, db_query_views)
    news_data["views"] = current_views
    return news_data


async def increase_news_views(db: AsyncSession, news_id: int):
    """原子自增新闻浏览量，并同步刷新缓存。

    顺序是：
    1. 先更新数据库，确保真实数据正确。
    2. 再刷新 views 缓存。
    3. 最后删除详情缓存，让下次详情读取拿到最新浏览量。
    """
    views_cache_key = f"news:views:{news_id}"

    stmt = update(News).where(News.id == news_id).values(views=News.views + 1)
    result: AsyncResult = await db.execute(stmt)
    await db.commit()
    success = result.rowcount > 0

    if success:
        async def db_query_new_views():
            """读取自增后的最新浏览量，并回填缓存。"""
            stmt = select(News.views).where(News.id == news_id)
            result = await db.execute(stmt)
            return result.scalar_one_or_none() or 0

        new_views = await db_query_new_views()
        await multi_level_cache.refresh(views_cache_key, new_views, ttl=86400)

        detail_cache_key = f"news:detail:{news_id}"
        await multi_level_cache.delete(detail_cache_key)

    return success


@multi_cache(key_prefix="news:related", expire=1800)
async def get_related_news(
    db: AsyncSession,
    news_id: int,
    category_id: int,
    limit: int = 5,
):
    """获取同分类相关推荐。

    当前策略比较简单：
    - 同分类
    - 排除当前新闻
    - 先按浏览量降序，再按发布时间降序

    它更像“热门相关推荐”而不是个性化推荐，但对资讯详情页已经够用。
    """
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
