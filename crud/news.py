"""CRUD 操作：针对新闻（news）和分类（category）的数据访问封装。

本模块提供了一组异步函数，用于读取新闻分类、新闻列表、新闻详情、
计数、相关内容以及增加阅读量等操作。

设计要点：
- 使用 SQLAlchemy 的异步会话（AsyncSession）进行数据库访问。
- 使用多级缓存（L1/L2）装饰器 `@multi_cache`、单级缓存 `@cache` 和
    `multi_level_cache` 的显式接口来降低数据库压力并提升响应速度。
- 返回的数据会使用 `jsonable_encoder` 做一次序列化，保证可以直接
    被 FastAPI 返回给客户端。
"""

from fastapi.encoders import jsonable_encoder
from sqlalchemy import select, func, update
from sqlalchemy.ext.asyncio import AsyncSession, AsyncResult

from models.news import Category, News
from cache.multi_level_cache import multi_level_cache, multi_cache
from cache.redis_cache import cache


@multi_cache(key_prefix="news:categories",expire=7200,hot=True)
async def get_categories(db: AsyncSession,skip: int = 0,limit: int = 100):
        """读取分类列表并缓存。

        缓存策略说明：
        - key 格式：`news:categories:skip={skip}:limit={limit}`。
        - `hot=True` 启用热点（逻辑过期）策略：数据在 L2 中永久保存，
            当过期时会异步后台更新缓存，而对外仍然返回旧值，减少读放大。

        参数：
        - db: SQLAlchemy 的异步会话对象。
        - skip/limit: 分页参数。

        返回：已序列化的分类列表（若无则返回空列表）。
        """
    stmt = select(Category).offset(skip).limit(limit)
    result = await db.execute(stmt)
    categories = result.scalars().all()
    return jsonable_encoder(categories) if categories else []


@multi_cache(key_prefix="news:list", expire=1800)
async def get_news_list(db: AsyncSession,category_id: int,skip: int = 0,limit: int = 10):
    """按分类读取新闻列表并缓存分页结果。

    缓存策略：
    - key 示例：`news:list:category_id=1:skip=0:limit=10`。
    - 使用两级缓存（L1 本地 + L2 Redis），减少频繁的数据库访问。

    返回：已序列化的新闻字典列表或空列表。
    """
    stmt = select(News).where(News.category_id == category_id).offset(skip).limit(limit)
    result = await db.execute(stmt)
    news_list = result.scalars().all()
    return jsonable_encoder(news_list) if news_list else []


@cache(key_prefix="news:count", expire=300)
async def get_news_count(db:AsyncSession,category_id: int):
    """获取指定分类下新闻的总数并缓存较短时间。

    仅缓存新闻计数以便快速响应分页请求的总页数计算。
    """

    stmt = select(func.count(News.id)).where(News.category_id == category_id)
    result = await db.execute(stmt)
    return result.scalar_one()


async def get_news_detail(db: AsyncSession,news_id: int):
    """获取单条新闻的详情，使用多级缓存以减少 DB 负载。

    缓存键：
    - 详情缓存：`news:detail:{news_id}`
    - 阅读量缓存：`news:views:{news_id}`

    流程：
    1. 通过 `multi_level_cache.get(detail_cache_key, db_query_detail)` 获取详情，
       若 L1/L2 都没有则回源查询数据库并缓存结果。
    2. 详情命中后，再去读取单独维护的阅读量缓存（views），将其注入到返回数据中。

    返回：包含字段 id,title,content,image,author,publish_time,category_id,views 的字典；
    若新闻不存在则返回 None。
    """

    detail_cache_key = f"news:detail:{news_id}"
    views_cache_key = f"news:views:{news_id}"

    async def db_query_detail():
        # 从 DB 查询新闻详情并转换为可序列化的字典结构
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
        # 单独读取当前的 views 值（避免与详情查询耦合）
        stmt = select(News.views).where(News.id == news_id)
        result = await db.execute(stmt)
        return result.scalar_one_or_none() or 0

    current_views = await multi_level_cache.get(views_cache_key, db_query_views)
    news_data["views"] = current_views

    return news_data


async def increase_news_views(db: AsyncSession,news_id: int):
    """对新闻的阅读量执行原子自增，并同步刷新相关缓存。

    步骤：
    1. 在 DB 层使用 `UPDATE ... SET views = views + 1` 执行自增，保证并发安全。
    2. 若更新成功，则重新读取最新的 views 值并刷新 views 缓存（TTL 可较长）。
    3. 删除该条新闻的详情缓存，保证下次读取详情能拿到最新的 views。

    返回：布尔值，表示是否成功更新（受影响的行数 > 0）。
    """

    views_cache_key = f"news:views:{news_id}"

    # 使用原子 SQL 更新语句增加 views
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
        # 刷新 views 缓存，长期保存（示例使用 86400 秒）
        await multi_level_cache.refresh(views_cache_key, new_views, ttl=86400)

        # 文章详情含有 views，需删除详情缓存让下次读取时回源以保证一致性
        detail_cache_key = f"news:detail:{news_id}"
        await multi_level_cache.delete(detail_cache_key)

    return success


@multi_cache(key_prefix="news:related",expire=1800)
async def get_related_news(db: AsyncSession,news_id: int,category_id: int,limit: int = 5):
    """获取与当前文章同分类的相关推荐（按 views 和 publish_time 排序）。

    逻辑说明：
    - 排序优先级：先按阅读量降序，再按发布时间降序，保证热门且新近的文章优先。
    - 返回结构为字典列表，字段命名尽量与前端约定一致（部分字段使用驼峰）。
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