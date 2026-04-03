# -*- coding: utf-8 -*-
"""
Celery 配置文件
"""
from kombu import Queue, Exchange

CELERY_BROKER_URL = "amqp://guest:guest@localhost:5672//"
CELERY_RESULT_BACKEND = "rpc://"

CELERY_TASK_SERIALIZER = "json"
CELERY_RESULT_SERIALIZER = "json"
CELERY_ACCEPT_CONTENT = ["json"]
CELERY_TIMEZONE = "Asia/Shanghai"
CELERY_ENABLE_UTC = False

CELERY_TASK_ACKS_LATE = True
CELERY_WORKER_PREFETCH_MULTIPLIER = 4
CELERY_TASK_MAX_RETRIES = 3
CELERY_TASK_DEFAULT_RETRY_DELAY = 60

CELERY_TASK_SOFT_TIME_LIMIT = 300
CELERY_TASK_TIME_LIMIT = 600

CELERY_TASK_QUEUES = (
    Queue("default", Exchange("default"), routing_key="default"),
    Queue("news", Exchange("news"), routing_key="news.#"),
    Queue("statistics", Exchange("statistics"), routing_key="statistics.#")
)

CELERY_TASK_DEFAULT_QUEUE = "default"

CELERY_TASK_ROUTES = {
    "tasks.news_tasks.*": {"queue": "news"},
    "tasks.news_spider_tasks.*": {"queue": "news"},
    "tasks.statistics_tasks.*": {"queue": "statistics"},
}

CELERY_BEAT_SCHEDULE = {
    "refresh-hot-news-every-hour": {
        "task": "tasks.statistics_tasks.refresh_hot_news",
        "schedule": 3600.0,
    },
    "fetch-news-every-6-hours": {
        "task": "tasks.news_spider_tasks.fetch_and_save_news",
        "schedule": 21600.0,
    },
}