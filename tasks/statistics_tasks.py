# -*- coding: utf-8 -*-
"""统计业务异步任务，包含热门新闻刷新、用户行为收集。"""

from middlewares.celery import celery_app
from utils.logger import get_logger

logger = get_logger(name="StatisticsTasks")


@celery_app.task(
    name="tasks.statistics_tasks.refresh_hot_news",
    queue="statistics"
)
def refresh_hot_news():
    """定时刷新热门新闻榜单。"""
    try:
        logger.info("刷新热门新闻榜单")
        return {"code": 200, "msg": "热榜刷新成功"}
    except Exception as e:
        logger.error(f"热榜刷新失败 | 错误={str(e)}")
        raise


@celery_app.task(
    name="tasks.statistics_tasks.collect_user_behavior",
    queue="statistics",
    rate_limit="500/m"
)
def collect_user_behavior(user_id: int, action: str, news_id: int):
    """收集用户行为：查看/点赞/分享/收藏。"""
    try:
        logger.info(f"收集用户行为 | user_id={user_id}, 行为={action}, news_id={news_id}")
        return {"code": 200, "msg": "行为收集成功"}
    except Exception as e:
        logger.error(f"行为收集失败 | 错误={str(e)}")
        raise