# -*- coding: utf-8 -*-
"""
新闻业务异步任务
包含：新闻热度更新、ES同步
"""
from celery import Task  # 从 celery 模块导入当前文件后续要用到的对象
from middlewares.celery import celery_app  # 从 middlewares.celery 模块导入当前文件后续要用到的对象
from utils.logger import get_logger  # 从 utils.logger 模块导入当前文件后续要用到的对象

logger = get_logger(name="NewsTasks")  # 把右边计算出来的结果保存到 logger 变量中，方便后面的代码继续复用


class NewsBaseTask(Task):  # 定义 NewsBaseTask 类，用来把这一块相关的状态和行为组织在一起
    """新闻任务基类：全局重试、退避策略"""
    autoretry_for = (Exception,)  # 把右边计算出来的结果保存到 autoretry_for 变量中，方便后面的代码继续复用
    retry_kwargs = {"max_retries": 3}  # 把右边计算出来的结果保存到 retry_kwargs 变量中，方便后面的代码继续复用
    retry_backoff = True  # 把右边计算出来的结果保存到 retry_backoff 变量中，方便后面的代码继续复用
    retry_backoff_max = 600  # 把右边计算出来的结果保存到 retry_backoff_max 变量中，方便后面的代码继续复用
    retry_jitter = True  # 把右边计算出来的结果保存到 retry_jitter 变量中，方便后面的代码继续复用


@celery_app.task(  # 使用 celery_app.task 装饰下面的函数或类，给它附加额外能力
    bind=True,  # 把右边计算出来的结果保存到 bind 变量中，方便后面的代码继续复用
    base=NewsBaseTask,  # 把右边计算出来的结果保存到 base 变量中，方便后面的代码继续复用
    name="tasks.news_tasks.increase_news_popularity",  # 把右边计算出来的结果保存到 name 变量中，方便后面的代码继续复用
    queue="news",  # 把右边计算出来的结果保存到 queue 变量中，方便后面的代码继续复用
    rate_limit="200/m"  # 把右边计算出来的结果保存到 rate_limit 变量中，方便后面的代码继续复用
)  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
def increase_news_popularity(self, news_id: int, increment: int = 1):  # 定义函数 increase_news_popularity，把一段可以复用的逻辑单独封装起来
    """异步更新新闻热度"""
    try:  # 开始尝试执行可能出错的逻辑，如果报错就会转到下面的异常分支
        logger.info(f"更新新闻热度 | news_id={news_id}, 增量={increment}")  # 记录一条日志，方便后续排查程序运行过程和定位问题
        return {"code": 200, "msg": "热度更新成功", "news_id": news_id}  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
    except Exception as e:  # 如果上面 try 里的代码报错，就进入这个异常处理分支
        logger.error(f"新闻热度更新失败 | news_id={news_id}, 错误={str(e)}")  # 记录一条日志，方便后续排查程序运行过程和定位问题
        raise self.retry(exc=e)  # 主动抛出异常，让上层知道这里出现了需要处理的问题


@celery_app.task(  # 使用 celery_app.task 装饰下面的函数或类，给它附加额外能力
    bind=True,  # 把右边计算出来的结果保存到 bind 变量中，方便后面的代码继续复用
    base=NewsBaseTask,  # 把右边计算出来的结果保存到 base 变量中，方便后面的代码继续复用
    name="tasks.news_tasks.sync_news_to_es",  # 把右边计算出来的结果保存到 name 变量中，方便后面的代码继续复用
    queue="news"  # 把右边计算出来的结果保存到 queue 变量中，方便后面的代码继续复用
)  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
def sync_news_to_es(self, news_id: int):  # 定义函数 sync_news_to_es，把一段可以复用的逻辑单独封装起来
    """异步同步新闻数据到Elasticsearch"""
    try:  # 开始尝试执行可能出错的逻辑，如果报错就会转到下面的异常分支
        logger.info(f"同步新闻到ES | news_id={news_id}")  # 记录一条日志，方便后续排查程序运行过程和定位问题
        return {"code": 200, "msg": "ES同步成功", "news_id": news_id}  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
    except Exception as e:  # 如果上面 try 里的代码报错，就进入这个异常处理分支
        logger.error(f"ES同步失败 | news_id={news_id}, 错误={str(e)}")  # 记录一条日志，方便后续排查程序运行过程和定位问题
        raise self.retry(exc=e)  # 主动抛出异常，让上层知道这里出现了需要处理的问题