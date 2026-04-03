# -*- coding: utf-8 -*-
"""
Celery Tasks 入口
导出 celery_app 供各任务模块使用
"""
from middlewares.celery import celery_app

__all__ = ["celery_app"]