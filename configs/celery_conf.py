# -*- coding: utf-8 -*-
"""
Celery 配置文件

【什么是 Celery？】
Celery 是一个强大的分布式任务队列系统，主要用于：
1. 异步执行耗时任务（如发送邮件、处理图片、爬虫抓取）
2. 定时执行任务（如每天凌晨统计数据、每小时刷新缓存）
3. 将耗时操作从主程序中剥离，提高系统响应速度

【架构说明】
Celery 采用"生产者-消费者"模式：
- 生产者：你的主程序（如 Flask 应用），负责发送任务到消息队列
- 消费者：Celery Worker（工作进程），负责从队列中取出任务并执行
- 消息队列：RabbitMQ 或 Redis，负责存储待执行的任务

                    ┌─────────────┐
                    │  Flask 应用  │ (生产者)
                    └──────┬──────┘
                           │ 发送任务
                           ▼
                    ┌─────────────┐
                    │   RabbitMQ   │ (消息队列/Broker)
                    └──────┬──────┘
                           │ 分发任务
              ┌────────────┼────────────┐
              ▼            ▼            ▼
        ┌──────────┐ ┌──────────┐ ┌──────────┐
        │ Worker 1 │ │ Worker 2 │ │ Worker 3 │ (消费者)
        └──────────┘ └──────────┘ └──────────┘
"""

from kombu import Queue, Exchange

# ============================================================================
# 第一部分：消息代理和结果存储配置
# ============================================================================

# 【CELERY_BROKER_URL】消息代理地址
# Celery 需要一个"中间人"来传递消息，这里使用的是 RabbitMQ
#
# URL 格式说明：amqp://用户名:密码@主机地址:端口/虚拟主机
# - amqp://：使用 AMQP 协议（RabbitMQ 使用的协议）
# - guest:guest：RabbitMQ 默认的用户名和密码（生产环境一定要改！）
# - localhost:5672：RabbitMQ 服务器地址和端口
# - //：最后的虚拟主机路径（默认是 "/"）
#
# 【为什么要用消息代理？】
# 想象一个餐厅：Flask 应用是"顾客"，Worker 是"厨师"
# 消息代理就是"服务员"，负责把顾客的订单（任务）传递给厨师
# 这样顾客不用等菜做完才能走，可以先离开（异步执行）
CELERY_BROKER_URL = "amqp://guest:guest@localhost:5672//"

# 【CELERY_RESULT_BACKEND】任务结果存储地址
# 任务执行完成后，结果需要存储在一个地方供后续查询
# 这里使用 RPC（远程过程调用）方式，通过消息队列返回结果
#
# 其他常用选项：
# - "rpc://"：通过消息队列返回结果（简单，但不持久化）
# - "redis://localhost:6379/0"：使用 Redis 存储（推荐，可持久化）
# - "db+sqlite:///results.db"：使用数据库存储
# - "cache+memcached://..."：使用缓存存储
#
# 【什么时候需要查询结果？】
# 例如：用户提交了一个"生成报表"的任务，想查询进度或获取报表下载链接
CELERY_RESULT_BACKEND = "rpc://"

# ============================================================================
# 第二部分：序列化配置
# ============================================================================

# 【CELERY_TASK_SERIALIZER】任务消息的序列化格式
# 将 Python 对象转换成可传输的格式（如字符串）
#
# 常用格式：
# - json：轻量、可读性好、跨语言支持（推荐）
# - pickle：支持更多 Python 对象类型，但安全性较低
# - msgpack：比 json 更快更小，但可读性差
# - yaml：可读性好，但速度较慢
#
# 【通俗理解】
# 序列化就像"打包行李"：把衣服（Python对象）装进箱子（json格式）
# 方便运输（网络传输），到达后再拆箱（反序列化）
CELERY_TASK_SERIALIZER = "json"

# 【CELERY_RESULT_SERIALIZER】任务结果的序列化格式
# 和上面的类似，只是针对执行结果的序列化
CELERY_RESULT_SERIALIZER = "json"

# 【CELERY_ACCEPT_CONTENT】接受的内容类型
# 为了安全，只接受 json 格式的消息
# 防止恶意用户发送 pickle 格式的代码注入攻击
#
# 【安全提示】
# pickle 格式可以序列化 Python 函数和对象，但也可能执行恶意代码
# 所以在生产环境中，建议只接受 json
CELERY_ACCEPT_CONTENT = ["json"]

# ============================================================================
# 第三部分：时区配置
# ============================================================================

# 【CELERY_TIMEZONE】设置 Celery 使用的时区
# 这对定时任务很重要！
# 例如：你想在"每天凌晨2点"执行任务，如果没有正确设置时区，
# 可能会在 UTC 时间凌晨2点（北京时间上午10点）执行
CELERY_TIMEZONE = "Asia/Shanghai"

# 【CELERY_ENABLE_UTC】是否使用 UTC 时间
# 设为 False 表示使用本地时区（上面的 Asia/Shanghai）
# 如果设为 True，所有时间都会转换成 UTC
CELERY_ENABLE_UTC = False

# ============================================================================
# 第四部分：任务执行策略配置
# ============================================================================

# 【CELERY_TASK_ACKS_LATE】延迟确认
# - True：任务执行完成后才确认（删除消息队列中的任务）
# - False：任务开始执行就确认
#
# 【为什么要设为 True？】
# 想象你在餐厅点了菜：
# - False（早确认）：服务员下单后就把订单撕了，
#   如果厨师突然辞职（Worker崩溃），你的菜就没了
# - True（晚确认）：厨师做完菜上桌后才撕订单，
#   如果厨师辞职，订单还在，可以换厨师做
#
# 简单说：防止任务在执行过程中因 Worker 崩溃而丢失
CELERY_TASK_ACKS_LATE = True

# 【CELERY_WORKER_PREFETCH_MULTIPLIER】预取倍数
# 每个 Worker 一次从队列中预先取出的任务数量
#
# 【通俗理解】
# 这就像厨师一次拿几个订单做：
# - 设为 1：一次只拿一个订单，做完再拿下一个
# - 设为 4：一次拿 4 个订单放在手边
#
# 【如何选择？】
# - 任务执行快（几秒）：可以设大一点（如 4-8），减少通信开销
# - 任务执行慢（几分钟）：设小一点（如 1），避免某个 Worker 抢走太多任务
# - 任务差异大：设为 1，让任务能均匀分配
CELERY_WORKER_PREFETCH_MULTIPLIER = 4

# 【CELERY_TASK_MAX_RETRIES】任务最大重试次数
# 如果任务执行失败（如网络错误），会自动重试
# 重试 3 次都失败后，才会标记为失败
#
# 【常见需要重试的场景】
# - 调用第三方 API（网络不稳定）
# - 数据库连接（偶发性连接失败）
# - 文件下载（服务器暂时不可用）
CELERY_TASK_MAX_RETRIES = 3

# 【CELERY_TASK_DEFAULT_RETRY_DELAY】重试间隔时间（秒）
# 每次重试之间等待 60 秒
#
# 【为什么要等待？】
# 如果服务器暂时不可用，立即重试可能还是失败
# 等待一段时间，给服务器恢复的机会
CELERY_TASK_DEFAULT_RETRY_DELAY = 60

# ============================================================================
# 第五部分：任务超时配置
# ============================================================================

# 【CELERY_TASK_SOFT_TIME_LIMIT】软超时时间（秒）
# 任务运行超过 300 秒（5分钟）后，会收到 SoftTimeLimitExceeded 异常
# 任务可以捕获这个异常，做清理工作后优雅退出
#
# 【通俗理解】
# 软超时就像"提醒"：哥们，你运行太久了，该收尾了
# 任务有机会做清理工作（如关闭文件、保存进度）
CELERY_TASK_SOFT_TIME_LIMIT = 300  # 5分钟

# 【CELERY_TASK_TIME_LIMIT】硬超时时间（秒）
# 任务运行超过 600 秒（10分钟）后，会被强制终止
# 任务无法捕获这个异常，直接被杀掉
#
# 【通俗理解】
# 硬超时就像"强制执行"：时间到，不管你在做什么，立刻停止！
# 所以软超时时间 < 硬超时时间，给任务留出清理时间
#
# 【为什么需要超时？】
# - 防止卡死的任务占用 Worker
# - 防止无限循环的任务
# - 资源合理分配
CELERY_TASK_TIME_LIMIT = 600  # 10分钟

# ============================================================================
# 第六部分：队列配置
# ============================================================================

# 【CELERY_TASK_QUEUES】定义任务队列
# 可以创建多个队列，让不同类型的任务走不同的队列
# 这样可以给不同队列分配不同数量的 Worker
#
# 【为什么需要多个队列？】
# 想象一个医院：
# - 急诊队列：处理紧急任务，分配更多医生（Worker）
# - 普通门诊队列：处理常规任务
# - 体检队列：处理耗时但不紧急的任务
#
# 这样紧急任务不会被大量普通任务堵塞
#
# 【Queue 参数说明】
# - 第一个参数：队列名称
# - Exchange：交换机，用于路由消息
# - routing_key：路由键，决定消息发到哪个队列
CELERY_TASK_QUEUES = (
    # 默认队列：处理通用任务
    Queue("default", Exchange("default"), routing_key="default"),

    # 新闻队列：专门处理新闻相关的任务
    # routing_key="news.#" 表示匹配所有以 "news." 开头的路由键
    # 例如：news.crawl, news.parse, news.publish 都会进入这个队列
    Queue("news", Exchange("news"), routing_key="news.#"),

    # 统计队列：专门处理统计相关的任务
    # 统计任务通常比较耗时，单独放一个队列避免影响其他任务
    Queue("statistics", Exchange("statistics"), routing_key="statistics.#")
)

# 【CELERY_TASK_DEFAULT_QUEUE】默认队列名称
# 如果任务没有指定队列，就发送到这个默认队列
CELERY_TASK_DEFAULT_QUEUE = "default"

# ============================================================================
# 第七部分：任务路由配置
# ============================================================================

# 【CELERY_TASK_ROUTES】任务路由规则
# 决定哪些任务进入哪个队列
#
# 【通俗理解】
# 这就像邮局的分拣员：
# - 看到"新闻类"邮件，扔进"新闻队列"箱子
# - 看到"统计类"邮件，扔进"统计队列"箱子
#
# 【路由规则格式】
# "任务模块路径": {"queue": "队列名称"}
#
# 使用通配符 * 匹配模块下的所有任务
CELERY_TASK_ROUTES = {
    # tasks/news_tasks.py 中的所有任务 → news 队列
    "tasks.news_tasks.*": {"queue": "news"},

    # tasks/news_spider_tasks.py 中的所有任务 → news 队列
    "tasks.news_spider_tasks.*": {"queue": "news"},

    # tasks/statistics_tasks.py 中的所有任务 → statistics 队列
    "tasks.statistics_tasks.*": {"queue": "statistics"},
}

# ============================================================================
# 第八部分：定时任务配置（Celery Beat）
# ============================================================================

# 【CELERY_BEAT_SCHEDULE】定时任务计划表
# Celery Beat 是一个调度器，会根据配置定时发送任务
#
# 【通俗理解】
# 这就像一个闹钟：到点就响（发送任务）
#
# 【配置格式】
# "任务名称": {
#     "task": "任务的完整路径",
#     "schedule": 时间间隔（秒），
#     "args": 位置参数（可选），
#     "kwargs": 关键字参数（可选）
# }
#
# 还可以使用 crontab 表达式设置更复杂的时间：
# from celery.schedules import crontab
# schedule: crontab(hour=7, minute=30)  # 每天7:30执行
CELERY_BEAT_SCHEDULE = {
    # 每小时刷新热门新闻
    # 3600 秒 = 1 小时
    "refresh-hot-news-every-hour": {
        "task": "tasks.statistics_tasks.refresh_hot_news",
        "schedule": 3600.0,  # 每 3600 秒（1小时）执行一次
    },

    # 每 6 小时抓取新闻
    # 21600 秒 = 6 小时
    "fetch-news-every-6-hours": {
        "task": "tasks.news_spider_tasks.fetch_and_save_news",
        "schedule": 21600.0,  # 每 21600 秒（6小时）执行一次
    },
}

# ============================================================================
# 补充说明：如何使用这个配置
# ============================================================================
#
# 【启动 Celery Worker（消费者）】
# 在终端运行：
# celery -A your_celery_app worker -l info
#
# -A your_celery_app：指定 Celery 应用实例
# worker：启动 worker 进程
# -l info：日志级别为 info
#
# 【启动 Celery Beat（定时调度器）】
# celery -A your_celery_app beat -l info
#
# 【同时启动 Worker 和 Beat】
# celery -A your_celery_app worker -B -l info
#
# 【指定队列启动 Worker】
# celery -A your_celery_app worker -Q news -l info  # 只处理 news 队列
# celery -A your_celery_app worker -Q news,statistics -l info  # 处理多个队列
#
# 【并发进程数】
# celery -A your_celery_app worker --concurrency=4 -l info
# --concurrency=4：启动 4 个并发进程
#
# ============================================================================
