# -*- coding: utf-8 -*-
"""新闻相关路由。

提供新闻分类、列表、详情等接口。
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from configs.db import get_db
from crud import news
from middlewares.token_bucket_rate_limit import rate_limit_dependency
from tasks.news_tasks import increase_news_popularity
from tasks.statistics_tasks import collect_user_behavior
from utils.logger import get_logger
from utils.response import success_response

router = APIRouter(
    prefix="/api/news",
    tags=["news"],
    dependencies=[Depends(rate_limit_dependency)],
)
logger = get_logger(name="NewsRouter")


@router.get("/categories")
async def get_news_categories(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
):
    """获取新闻分类列表。"""
    categories = await news.get_categories(db, skip, limit)
    return success_response(message="获取分类成功", data=categories)


@router.get("/list")
async def get_news_list(
    db: AsyncSession = Depends(get_db),
    category_id: int = Query(..., ge=1, alias="categoryId"),
    page: int = Query(1, ge=1, alias="page"),
    page_size: int = Query(10, le=100, alias="pageSize"),
):
    """分页获取新闻列表。"""
    offset = (page - 1) * page_size
    news_list = await news.get_news_list(db, category_id, offset, page_size)
    total = await news.get_news_count(db, category_id)
    has_more = (offset + len(news_list)) < total

    return success_response(
        message="获取新闻列表成功",
        data={"list": news_list, "total": total, "hasMore": has_more},
    )


@router.get("/detail")
async def get_news_detail(
    db: AsyncSession = Depends(get_db),
    news_id: int = Query(..., alias="id"),
):
    """获取新闻详情，同时递增浏览量并返回相关推荐。"""
    # 递增浏览量
    views_updated = await news.increase_news_views(db, news_id)
    if not views_updated:
        raise HTTPException(status_code=404, detail="更新新闻浏览量失败")

    # 获取详情
    news_detail = await news.get_news_detail(db, news_id)
    if not news_detail:
        raise HTTPException(status_code=404, detail="新闻不存在")

    # 获取相关推荐
    related_news = await news.get_related_news(db, news_id, news_detail["category_id"])

    # 异步派发热度和行为统计任务
    try:
        increase_news_popularity.delay(news_id, 1)
    except Exception as exc:
        logger.warning("派发新闻热度任务失败", news_id=news_id, error=str(exc))

    try:
        collect_user_behavior.delay(0, "view", news_id)
    except Exception as exc:
        logger.warning("派发用户行为任务失败", news_id=news_id, error=str(exc))

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
