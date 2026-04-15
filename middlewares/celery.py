# -*- coding: utf-8 -*-
"""
Celery 应用入口
"""
from celery import Celery  # 从 celery 模块导入当前文件后续要用到的对象
from utils.logger import get_logger  # 从 utils.logger 模块导入当前文件后续要用到的对象

logger = get_logger(name="Celery")  # 把右边计算出来的结果保存到 logger 变量中，方便后面的代码继续复用


def create_celery_app() -> Celery:  # 定义函数 create_celery_app，把一段可以复用的逻辑单独封装起来
    """创建并初始化 Celery 应用"""
    app = Celery("toutiao")  # 把右边计算出来的结果保存到 app 变量中，方便后面的代码继续复用
    app.config_from_object("configs.celery", namespace="CELERY")  # 继续调用应用对象的方法，完成注册、配置或挂载等动作
    app.autodiscover_tasks(["tasks"])  # 继续调用应用对象的方法，完成注册、配置或挂载等动作
    logger.info("Celery 应用初始化完成")  # 记录一条日志，方便后续排查程序运行过程和定位问题
    return app  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束


celery_app = create_celery_app()  # 这里创建一个全局可复用的运行时资源，避免后面每次都重复初始化
