# -*- coding: utf-8 -*-
"""Celery 异步任务队列配置模块。

本模块负责配置 Celery 分布式任务队列，用于处理耗时操作。

Celery 在项目中的作用：
-----------------------
1. 新闻抓取：定时从外部网站抓取新闻，避免阻塞主服务
2. 热度统计：定期计算新闻热度，更新排行榜
3. 数据同步：批量数据处理和迁移

核心概念：
----------
- Broker（消息代理）：RabbitMQ，负责存储和转发任务消息
- Worker（工作者）：执行任务的进程，可以部署多个实例
- Beat（调度器）：定时触发任务，类似 crontab
- Result Backend：存储任务结果，这里用 RPC 方式

配置分组：
----------
1. 消息代理配置：连接 RabbitMQ
2. 序列化配置：统一使用 JSON
3. 时区配置：使用国内时区
4. 可靠性配置：延迟确认、限流、重试
5. 超时配置：防止任务卡死
6. 队列配置：按业务拆分队列
7. 路由配置：任务分发规则
8. 定时任务配置：周期性任务调度
"""

from __future__ import annotations

from kombu import Exchange, Queue
from urllib.parse import quote

from configs.settings import get_settings

settings = get_settings()

# ==============================================================================
# 消息代理与结果后端配置
# ==============================================================================
# Broker URL 格式：amqp://user:password@host:port/vhost
# vhost 需要 URL 编码，因为可能包含特殊字符（如 /）
# Result Backend 使用 RPC 方式，任务结果通过消息队列返回
# ==============================================================================

CELERY_BROKER_URL = (
    f"amqp://{settings.RABBITMQ_USER}:{settings.RABBITMQ_PASSWORD}"
    f"@{settings.RABBITMQ_HOST}:{settings.RABBITMQ_PORT}/{quote(settings.RABBITMQ_VHOST, safe='')}"
)
CELERY_RESULT_BACKEND = "rpc://"  # 使用 RPC 作为结果后端

# ==============================================================================
# 序列化配置
# ==============================================================================
# 统一使用 JSON 序列化，原因：
# - JSON 是通用格式，跨语言兼容性好
# - pickle 有安全风险，不推荐使用
# - msgpack 虽然更高效，但需要额外依赖
# ==============================================================================

CELERY_TASK_SERIALIZER = "json"  # 任务参数序列化格式
CELERY_RESULT_SERIALIZER = "json"  # 任务结果序列化格式
CELERY_ACCEPT_CONTENT = ["json"]  # 只接受 JSON 格式的消息

# ==============================================================================
# 时区配置
# ==============================================================================
# 使用国内时区（Asia/Shanghai），而非 UTC
# 这样定时任务的时间更直观，日志时间也更容易理解
# ==============================================================================

CELERY_TIMEZONE = "Asia/Shanghai"
CELERY_ENABLE_UTC = False  # 禁用 UTC，使用本地时区

# ==============================================================================
# 任务可靠性配置
# ==============================================================================
# 这些配置保证任务不会丢失，即使 Worker 崩溃也能恢复
#
# ACKS_LATE（延迟确认）：
# - 默认情况下，任务从队列取出后立即确认
# - 开启后，任务执行成功才确认
# - 如果 Worker 崩溃，未完成的任务会被其他 Worker 重新执行
#
# PREFETCH_MULTIPLIER（预取倍数）：
# - 控制 Worker 一次从队列取多少任务
# - 值越大吞吐量越高，但任务分配可能不均衡
# - 建议值：CPU 核心数 * 2
# ==============================================================================

CELERY_TASK_ACKS_LATE = True  # 任务执行成功后才确认
CELERY_WORKER_PREFETCH_MULTIPLIER = 4  # 每个 Worker 预取 4 个任务
CELERY_TASK_MAX_RETRIES = 3  # 任务失败最多重试 3 次
CELERY_TASK_DEFAULT_RETRY_DELAY = 60  # 重试间隔 60 秒

# ==============================================================================
# 任务超时配置
# ==============================================================================
# 防止单个任务执行时间过长，占用 Worker 资源
#
# SOFT_TIME_LIMIT（软超时）：
# - 超时后抛出 SoftTimeLimitExceeded 异常
# - 任务可以捕获异常，做清理工作后优雅退出
#
# TIME_LIMIT（硬超时）：
# - 超时后强制终止任务，无法捕获
# - 作为最后保障，确保任务不会无限执行
# ==============================================================================

CELERY_TASK_SOFT_TIME_LIMIT = 300  # 软超时 5 分钟
CELERY_TASK_TIME_LIMIT = 600  # 硬超时 10 分钟

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
