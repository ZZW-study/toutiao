# -*- coding: utf-8 -*-
"""
新闻爬虫 Celery 定时任务
"""
from middlewares.celery import celery_app
from services.news_spider import NewsSpiderService
from crud.news_spider import NewsSpiderCRUD
from configs.db_conf import AsyncSessionLocal
from utils.logger import get_logger

logger = get_logger(name="NewsSpiderTasks")


@celery_app.task(
    name="tasks.news_spider_tasks.fetch_and_save_news",
    queue="news",
    bind=True,
    max_retries=3,
    default_retry_delay=300
)
def fetch_and_save_news(self):
    """
    定时抓取新闻并保存到数据库
    每6小时执行一次（可在 celery_conf.py 中配置）
    """
    import asyncio

    async def _execute():
        async with AsyncSessionLocal() as db:
            try:
                await NewsSpiderCRUD.ensure_categories(db)

                news_list = await NewsSpiderService.fetch_all_news()

                if not news_list:
                    logger.warning("本次抓取未获取到任何新闻")
                    return {"status": "success", "saved": 0}

                result = await NewsSpiderCRUD.save_news_batch(db, news_list)
                logger.info(f"新闻爬取任务完成: {result}")
                return {"status": "success", **result}

            except Exception as e:
                logger.error(f"新闻爬取任务失败: {str(e)}")
                raise self.retry(exc=e)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_execute())
    finally:
        loop.close()


@celery_app.task(
    name="tasks.news_spider_tasks.fetch_sina_news",
    queue="news"
)
def fetch_sina_news():
    """单独抓取新浪新闻"""
    import asyncio

    async def _execute():
        async with AsyncSessionLocal() as db:
            try:
                news_list = await NewsSpiderService.fetch_sina_news()
                if not news_list:
                    return {"status": "success", "saved": 0}
                result = await NewsSpiderCRUD.save_news_batch(db, news_list)
                return {"status": "success", **result}
            except Exception as e:
                logger.error(f"新浪新闻爬取失败: {str(e)}")
                return {"status": "error", "message": str(e)}

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_execute())
    finally:
        loop.close()


@celery_app.task(
    name="tasks.news_spider_tasks.fetch_qq_news",
    queue="news"
)
def fetch_qq_news():
    """单独抓取腾讯新闻"""
    import asyncio

    async def _execute():
        async with AsyncSessionLocal() as db:
            try:
                news_list = await NewsSpiderService.fetch_qq_news()
                if not news_list:
                    return {"status": "success", "saved": 0}
                result = await NewsSpiderCRUD.save_news_batch(db, news_list)
                return {"status": "success", **result}
            except Exception as e:
                logger.error(f"腾讯新闻爬取失败: {str(e)}")
                return {"status": "error", "message": str(e)}

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(_execute())
    finally:
        loop.close()
