"""新闻相关的路由定义。

包含的接口：
1. 获取分类（/categories）
2. 获取新闻列表（/list）
3. 获取新闻详情及相关推荐（/detail）

路由负责：
- 参数验证与限流中间件（rate limit）
- 调用 CRUD 层获取数据
- 触发异步任务（统计/热度相关）
- 统一返回成功响应
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from configs.db_conf import get_db
from crud import news
from tasks.news_tasks import increase_news_popularity
from tasks.statistics_tasks import collect_user_behavior
from utils.response import success_response
from middlewares.token_bucket_rate_limit import rate_limit_dependency


router = APIRouter(prefix="/api/news", tags=["news"])


@router.get("/categories")
async def get_news_categories(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    _: None = Depends(rate_limit_dependency)
):
    """获取新闻分类列表。

    参数：
    - skip/limit: 分页参数

    返回值：统一的 success_response，data 部分为分类列表。
    """
    categories = await news.get_categories(db, skip, limit)
    return success_response(message="获取分类成功", data=categories)


@router.get("/list")
async def get_news_list(
    db: AsyncSession = Depends(get_db),
    category_id: int = Query(..., ge=1, alias="categoryId"),
    page: int = Query(1, ge=1, alias="page"),
    page_size: int = Query(10, le=100, alias="pageSize"),
    _: None = Depends(rate_limit_dependency)
):
    offset = (page - 1) * page_size

    # 从 CRUD 层获取分页列表与总数
    news_list = await news.get_news_list(db, category_id, offset, page_size)
    total = await news.get_news_count(db, category_id)
    has_more = (offset + len(news_list)) < total

    return success_response(
        message="获取新闻列表成功",
        data={
            "list": news_list,
            "total": total,
            "hasMore": has_more,
        },
    )


@router.get("/detail")
async def get_news_detail(
    db: AsyncSession=Depends(get_db),
    news_id: int = Query(...,alias="id"),
    _: None = Depends(rate_limit_dependency)
):
    """获取新闻详情接口。

    流程：
    1. 先对阅读量做自增（优化：先自增再读取详情，可以把最新的 views 注入到详情中）。
    2. 查询详情并获取相关推荐。
    3. 触发异步任务：增加热度统计与记录用户行为（Celery 异步）。
    4. 返回格式化后的详情数据与相关推荐。
    """

    views_res = await news.increase_news_views(db, news_id)
    if not views_res:
        raise HTTPException(status_code=404, detail="更新新闻浏览量失败")

    news_detail = await news.get_news_detail(db, news_id)
    if not news_detail:
        raise HTTPException(status_code=404, detail="新闻不存在")

    related_news = await news.get_related_news(db, news_id, news_detail["category_id"])

    # 触发后台任务：更新热度、统计用户行为（非阻塞）
    increase_news_popularity.delay(news_id, 1)
    collect_user_behavior.delay(news_detail["id"], "view", news_id)

    return success_response(
        message="获取新闻详情成功",
        data={
            "id": news_detail["id"],
            "title": news_detail["title"],
            "content": news_detail["content"],
            "image": news_detail["image"],
            "author": news_detail["author"],
            "publishTime": news_detail["publish_time"],
            "categoryId": news_detail["category_id"],
            "views": news_detail["views"],
            "relatedNews": related_news,
        },
    )
