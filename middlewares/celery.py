# -*- coding: utf-8 -*-
"""
Celery 应用入口
"""
from celery import Celery
from utils.logger import get_logger

logger = get_logger(name="Celery")


def create_celery_app() -> Celery:
    """创建并初始化 Celery 应用"""
    app = Celery("toutiao")
    app.config_from_object("configs.celery_conf", namespace="CELERY")
    app.autodiscover_tasks(["tasks"])
    logger.info("Celery 应用初始化完成")
    return app


celery_app = create_celery_app()