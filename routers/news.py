#1.新闻分类 2.新闻列表 3.点击新闻就跳转到详细内容页面及相关推荐
from fastapi import APIRouter,Depends, HTTPException,Query
from sqlalchemy.ext.asyncio import AsyncSession
from configs.db_conf import get_db
from crud import news
from tasks.news_tasks import increase_news_popularity
from tasks.statistics_tasks import collect_user_behavior
from utils.response import success_response
from middlewares.token_bucket_rate_limit import rate_limit_dependency

router = APIRouter(prefix="/api/news",tags=["news"])


@router.get("/categories")
async def get_news_categories(
    db: AsyncSession = Depends(get_db),
    skip: int = 0,
    limit: int = 100,
    _: None = Depends(rate_limit_dependency)
):
    categories = await news.get_categories(db,skip,limit)
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

    news_list = await news.get_news_list(db,category_id,offset,page_size)
    total = await news.get_news_count(db,category_id)
    has_more = (offset + len(news_list)) < total

    return success_response(message="获取新闻列表成功", data={
        "list": news_list,
        "total": total,
        "hasMore": has_more
    })


@router.get("/detail")
async def get_news_detail(
    db: AsyncSession=Depends(get_db),
    news_id: int = Query(...,alias="id"),
    _: None = Depends(rate_limit_dependency)
):
    views_res = await news.increase_news_views(db,news_id)
    if not views_res:
        raise HTTPException(status_code=404,detail="更新新闻浏览量失败")

    news_detail = await news.get_news_detail(db,news_id)
    if not news_detail:
        raise HTTPException(status_code=404,detail="新闻不存在")

    related_news = await news.get_related_news(db,news_id,news_detail["category_id"])

    increase_news_popularity.delay(news_id, 1)
    collect_user_behavior.delay(news_detail["id"], "view", news_id)

    return success_response(message="获取新闻详情成功", data={
        "id": news_detail["id"],
        "title": news_detail["title"],
        "content": news_detail["content"],
        "image": news_detail["image"],
        "author": news_detail["author"],
        "publishTime": news_detail["publish_time"],
        "categoryId": news_detail["category_id"],
        "views": news_detail["views"],
        "relatedNews": related_news
    })
