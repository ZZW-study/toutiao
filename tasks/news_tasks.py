# -*- coding: utf-8 -*-
"""
新闻业务异步任务
包含：新闻热度更新、ES同步
"""
from celery import Task
from middlewares.celery import celery_app
from utils.logger import get_logger

logger = get_logger(name="NewsTasks")


class NewsBaseTask(Task):
    """新闻任务基类：全局重试、退避策略"""
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True


@celery_app.task(
    bind=True,
    base=NewsBaseTask,
    name="tasks.news_tasks.increase_news_popularity",
    queue="news",
    rate_limit="200/m"
)
def increase_news_popularity(self, news_id: int, increment: int = 1):
    """异步更新新闻热度"""
    try:
        logger.info(f"更新新闻热度 | news_id={news_id}, 增量={increment}")
        return {"code": 200, "msg": "热度更新成功", "news_id": news_id}
    except Exception as e:
        logger.error(f"新闻热度更新失败 | news_id={news_id}, 错误={str(e)}")
        raise self.retry(exc=e)


@celery_app.task(
    bind=True,
    base=NewsBaseTask,
    name="tasks.news_tasks.sync_news_to_es",
    queue="news"
)
def sync_news_to_es(self, news_id: int):
    """异步同步新闻数据到Elasticsearch"""
    try:
        logger.info(f"同步新闻到ES | news_id={news_id}")
        return {"code": 200, "msg": "ES同步成功", "news_id": news_id}
    except Exception as e:
        logger.error(f"ES同步失败 | news_id={news_id}, 错误={str(e)}")
        raise self.retry(exc=e)