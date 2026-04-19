# -*- coding: utf-8 -*-
"""Celery 异步任务队列配置模块。"""

from __future__ import annotations

from kombu import Exchange, Queue
from urllib.parse import quote
from configs.settings import get_settings

settings = get_settings()

# ==============================================================================
# 消息代理与结果后端配置
# ==============================================================================

CELERY_BROKER_URL = (
    f"amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASSWORD}"
    f"@{settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}/{quote(settings.RABBITMQ_VHOST, safe='')}"
)
CELERY_RESULT_BACKEND = "rpc://"  # 使用 RPC 作为结果后端

# ==============================================================================
# 序列化配置
# ==============================================================================

CELERY_TASK_SERIALIZER = "json"  # 任务参数序列化格式
CELERY_RESULT_SERIALIZER = "json"  # 任务结果序列化格式
CELERY_ACCEPT_CONTENT = ["json"]  # 只接受 JSON 格式的消息

# ==============================================================================
# 时区配置
# ==============================================================================

CELERY_TIMEZONE = "Asia/Shanghai"
CELERY_ENABLE_UTC = False  # 禁用 UTC，使用本地时区

# ==============================================================================
# 任务可靠性配置
# ==============================================================================
CELERY_TASK_ACKS_LATE = True            # 任务执行成功后才确认
CELERY_WORKER_PREFETCH_MULTIPLIER = 4   # 每个 Worker 预取 4 个任务
CELERY_TASK_MAX_RETRIES = 3             # 任务失败最多重试 3 次
CELERY_TASK_DEFAULT_RETRY_DELAY = 60    # 重试间隔 60 秒

# ==============================================================================
# 任务超时配置
# ==============================================================================

CELERY_TASK_SOFT_TIME_LIMIT = 600   # 软超时 10 分钟
CELERY_TASK_TIME_LIMIT = 1200       # 硬超时 20 分钟

# ==============================================================================
# 队列配置
# ==============================================================================
# 按业务拆分队列，避免互相影响：
# - default: 默认队列，处理一般任务
# - news: 新闻相关任务（抓取、索引）
# - statistics: 统计相关任务（热度计算、排行榜）
#
# 每个队列可以启动独立的 Worker，实现资源隔离
# 例如：celery -A main worker -Q news -c 2
# ==============================================================================

CELERY_TASK_QUEUES = (
    Queue("default", Exchange("default"), routing_key="default"),
    Queue("news", Exchange("news"), routing_key="news.#"),
    Queue("statistics", Exchange("statistics"), routing_key="statistics.#"),
)

CELERY_TASK_DEFAULT_QUEUE = "default"

# ==============================================================================
# 任务路由配置
# ==============================================================================
# 根据任务名称自动分发到对应队列
# 路由规则使用通配符匹配：
# - tasks.news_tasks.*: 匹配 news_tasks 模块下的所有任务
# - tasks.statistics_tasks.*: 匹配 statistics_tasks 模块下的所有任务
# ==============================================================================

CELERY_TASK_ROUTES = {
    "tasks.news_tasks.*": {"queue": "news"},
    "tasks.news_spider_tasks.*": {"queue": "news"},
    "tasks.statistics_tasks.*": {"queue": "statistics"},
}

# ==============================================================================
# 定时任务配置（Celery Beat）
# ==============================================================================
# 使用 Celery Beat 实现周期性任务调度
# schedule 值为执行间隔（秒）
#
# 配置的任务：
# - refresh_hot_news: 每小时刷新一次热门新闻
# - fetch_and_save_news: 每 6 小时抓取一次新闻
# ==============================================================================

CELERY_BEAT_SCHEDULE = {
    "refresh-hot-news-every-hour": {
        "task": "tasks.statistics_tasks.refresh_hot_news",
        "schedule": 3600.0,  # 每小时执行一次
    },
    "fetch-news-every-6-hours": {
        "task": "tasks.news_spider_tasks.fetch_and_save_news",
        "schedule": 21600.0,  # 每 6 小时执行一次
    },
}
