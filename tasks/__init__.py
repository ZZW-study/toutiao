# -*- coding: utf-8 -*-
"""
Celery Tasks 入口
导出 celery_app 供各任务模块使用
"""
from middlewares.celery import celery_app  # 从 middlewares.celery 模块导入当前文件后续要用到的对象

__all__ = ["celery_app"]  # 把右边计算出来的结果保存到 __all__ 变量中，方便后面的代码继续复用