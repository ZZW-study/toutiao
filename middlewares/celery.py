# -*- coding: utf-8 -*-
"""
Celery 应用入口
"""
from celery import Celery
from utils.logger import get_logger

logger = get_logger(name="Celery")


def create_celery_app() -> Celery:
    """创建并初始化 Celery 应用"""
    # 以 "toutiao" 为名创建实例，从统一配置模块加载参数，并自动发现 tasks 包下的任务
    app = Celery("toutiao")
    app.config_from_object("configs.celery", namespace="CELERY")
    app.autodiscover_tasks(["tasks"])
    logger.info("Celery 应用初始化完成")
    return app


# 模块级单例，避免每次导入都重复初始化
celery_app = create_celery_app()
