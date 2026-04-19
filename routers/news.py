# -*- coding: utf-8 -*-
"""新闻相关路由。

提供新闻分类、列表、详情等接口。
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession

from configs.db import get_db
from crud import news
from tasks.news_tasks import increase_news_popularity
from tasks.statistics_tasks import collect_user_behavior
from utils.logger import get_logger
from utils.response import success_response

router = APIRouter(
    prefix="/api/news",
    tags=["news"],
)
logger = get_logger(name="NewsRouter")
# 当点击链接、在地址栏回车、或者用 fetch 发一个简单请求时，以为只发送了 https://example.com/categories，但真实发送的 HTTP 报文远比这个复杂。

# 一个真实 HTTP GET 请求的样子（你点一下浏览器）
# 假设你访问 http://localhost:8000/categories，浏览器实际发出的报文大致如下：

# http
# GET /categories HTTP/1.1
# Host: localhost:8000
# User-Agent: Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 ...
# Accept: text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8
# Accept-Language: zh-CN,zh;q=0.9
# Accept-Encoding: gzip, deflate, br
# Connection: keep-alive
# Cookie: sessionid=abc123; token=xyz
# Upgrade-Insecure-Requests: 1
# Sec-Fetch-Dest: document
# Sec-Fetch-Mode: navigate
# Sec-Fetch-Site: none
# ...
# 除了 /categories 这个 URL 路径，还发送了：
# 请求方法：GET
# HTTP 版本：HTTP/1.1
# Host：服务器的主机名和端口
# User-Agent：你的浏览器类型、操作系统等
# Accept：客户端能处理的媒体类型
# Accept-Language：偏好的语言
# Accept-Encoding：支持的压缩算法
# Connection：连接控制
# Cookie：本地存储的网站数据（如果有）
# 以及很多浏览器自动添加的头部（如 Sec-Fetch-* 等安全相关头）

# skip 和 limit：是查询参数（Query Parameters），FastAPI 默认会将非依赖项的简单类型参数（如 int、str）视为查询参数。
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

    # ========== Celery 异步任务调用 ==========
    # increase_news_popularity 是被 @celery_app.task 装饰的函数
    # 装饰器把它包装成了 Task 对象，附加了 delay()、apply_async() 等方法
    #
    # .delay() 的作用：
    #   1. 将任务参数序列化为 JSON
    #   2. 构造任务消息，发送到 RabbitMQ 队列
    #   3. 立即返回 AsyncResult 对象，不等待任务执行
    #
    # 执行流程：
    #   API 请求 → delay() 发消息到队列 → 立即返回响应给用户
    #                                    ↓
    #                              Worker 从队列取出任务 → 执行任务函数
    #
    # 好处：用户请求不会被阻塞，耗时操作在后台异步完成
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
