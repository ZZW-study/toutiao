# -*- coding: utf-8 -*-
"""Celery 异步任务队列配置模块。"""

from __future__ import annotations

from kombu import Queue
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
# 任务触发方式说明
# ==============================================================================
#
# Celery 任务有两种触发方式：
#
# 一、定时触发（需要启动 Celery Beat）
# ----------------------------
# 由 Celery Beat 调度器按 schedule 自动触发，无需人工干预。
#
# 启动命令：
#   celery -A middlewares.celery beat -l info
#
# 流程：
#   Celery Beat（定时调度器）
#       ↓ 每 N 秒/分钟/小时
#   发送任务消息到 RabbitMQ 队列
#       ↓
#   Celery Worker 从队列消费任务
#       ↓
#   执行任务函数（如 fetch_and_save_news）
#       ↓
#   结果存入数据库
#
# 二、代码调用触发（只需启动 Celery Worker）
# ----------------------------------
# 在业务代码中通过 .delay() 或 .apply_async() 显式触发。
#
# 示例（routers/news.py）：
#   increase_news_popularity.delay(news_id, 1)  # 用户查看新闻时触发
#   collect_user_behavior.delay(0, "view", news_id)
#
# 流程：
#   用户请求 API（如 GET /news/{id}）
#       ↓
#   路由处理函数中调用 task.delay()
#       ↓
#   任务消息发送到 RabbitMQ 队列
#       ↓
#   Celery Worker 从队列消费并执行
#       ↓
#   主线程立即返回响应，不阻塞用户请求
#
# 三、总结
# --------
# | 触发方式   | 启动组件          | 适用场景           |
# |------------|-------------------|--------------------|
# | 定时触发   | Worker + Beat     | 定期爬取、定时刷新 |
# | 代码调用   | Worker            | 用户行为、异步处理 |
#
# ==============================================================================


# ==============================================================================
# 队列配置
# ==============================================================================
# 定义任务队列，Celery 使用默认的 direct exchange 按队列名路由
#
# 队列作用：隔离不同类型的任务，可启动多个 Worker 分别消费不同队列
#   - default: 默认队列，处理通用任务
#   - news: 新闻相关任务（爬取、热度更新、ES同步）
#   - statistics: 统计相关任务（热榜刷新、行为收集）
#
CELERY_TASK_QUEUES = (
    Queue("default"),
    Queue("news"),
    Queue("statistics"),
)

CELERY_TASK_DEFAULT_QUEUE = "default"

# ==============================================================================
# 任务路由规则配置
# ==============================================================================
# 根据任务名模式匹配，将任务分发到指定队列
#
# 规则说明：
#   "tasks.news_tasks.*" 匹配 tasks.news_tasks 下的所有任务
#   任务会自动路由到对应的队列，无需在 @task 装饰器中指定 queue
#
CELERY_TASK_ROUTES = {
    "tasks.news_tasks.*": {"queue": "news"},
    "tasks.news_spider_tasks.*": {"queue": "news"},
    "tasks.statistics_tasks.*": {"queue": "statistics"},
}

# ==============================================================================
# 定时任务配置（Celery Beat）
# ==============================================================================
# 定义定时任务，需要启动 Celery Beat 调度器才会生效
#
# 启动 Beat：
#   celery -A middlewares.celery beat -l info
#
# 或与 Worker 合并启动（仅开发环境）：
#   celery -A middlewares.celery worker -B -l info -P eventlet
#
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
