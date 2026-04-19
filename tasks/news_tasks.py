# -*- coding: utf-8 -*-
"""新闻业务异步任务，包含热度更新、ES同步。"""

from celery import Task
from middlewares import celery_app
from utils.logger import get_logger

logger = get_logger(name="NewsTasks")


class NewsBaseTask(Task):
    """新闻任务基类：全局重试、退避策略。"""
    autoretry_for = (Exception,)
    retry_kwargs = {"max_retries": 3}
    retry_backoff = True
    retry_backoff_max = 600
    retry_jitter = True

# =============================================================================
# Celery 任务装饰器执行流程（带参数）
# =============================================================================
# 1. 模块加载时，Python 解释器解析 @celery_app.task(...) 装饰器
# 2. 装饰器参数被打包为字典: {bind, base, name, rate_limit}
# 3. 执行装饰器函数celery_app.task(**params) ，又返回一个装饰器内部的函数
# 4. 原函数被传入这个内部的函数，返回 Celery Task 代理对象
# 5. 对象又.delay()方法，调用 .delay() 时，可传入参数，然后可将参数解析后，可执行里面的逻辑，而且还可以执行这个被装饰的函数，任务被序列化并发送到消息队列，由 Worker 执行
# =============================================================================
@celery_app.task(
    bind=True,        # 绑定 self，使任务函数可访问自身实例（用于 self.retry()）
    base=NewsBaseTask,  # 继承自定义基类，复用重试策略、退避配置等通用逻辑
    name="tasks.news_tasks.increase_news_popularity",  # 任务唯一标识，用于路由和监控
    rate_limit="200/m"  # 速率限制：每分钟最多执行 200 次，防止数据库压力过大
)
def increase_news_popularity(self, news_id: int, increment: int = 1):
    """异步更新新闻热度。

    调用方式:
        increase_news_popularity.delay(news_id=123, increment=1)  # 异步发送到队列
        increase_news_popularity(news_id=123, increment=1)        # 同步直接执行（调试用）
    """
    try:
        logger.info(f"更新新闻热度 | news_id={news_id}, 增量={increment}")
        return {"code": 200, "msg": "热度更新成功", "news_id": news_id}
    except Exception as e:
        logger.error(f"新闻热度更新失败 | news_id={news_id}, 错误={str(e)}")
        raise self.retry(exc=e)  # bind=True 时可用 self.retry() 重试


