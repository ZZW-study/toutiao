# -*- coding: utf-8 -*-
"""
Celery 应用入口
"""
from celery import Celery
from utils.logger import get_logger

logger = get_logger(name="Celery")


def create_celery_app() -> Celery:
    """创建并初始化 Celery 应用，就是创建Celery实例类-->加载配置-->加载任务"""
    # 以 "toutiao" 为名创建实例，从统一配置模块加载参数，并自动发现 tasks 包下的任务
    app = Celery("toutiao")

    # 读取 configs.celery 模块中所有以 CELERY_ 开头的变量（如 CELERY_BROKER_URL、CELERY_TASK_ROUTES 等）。
    # 去掉 CELERY_ 前缀后，作为 Celery 的配置项生效。
    # 例如：模块中的 CELERY_BROKER_URL → app.conf.broker_url。
    app.config_from_object("configs.celery", namespace="CELERY")

    # 扫描 tasks 包（Python 包，包含 __init__.py）下的所有子模块。
    # 寻找被 @app.task 装饰的函数，注册为 Celery 任务。
    # 这些任务会遵循配置中的 CELERY_TASK_ROUTES 路由规则，自动分配到对应队列。
    app.autodiscover_tasks(["tasks"])
    logger.info("Celery 应用初始化完成")
    return app


# 模块级单例，避免每次导入都重复初始化
celery_app = create_celery_app()
