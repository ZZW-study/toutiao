# -*- coding: utf-8 -*-
"""
统计业务异步任务
包含：热门新闻刷新、用户行为收集
"""
from middlewares.celery import celery_app  # 从 middlewares.celery 模块导入当前文件后续要用到的对象
from utils.logger import get_logger  # 从 utils.logger 模块导入当前文件后续要用到的对象

logger = get_logger(name="StatisticsTasks")  # 把右边计算出来的结果保存到 logger 变量中，方便后面的代码继续复用


@celery_app.task(  # 使用 celery_app.task 装饰下面的函数或类，给它附加额外能力
    name="tasks.statistics_tasks.refresh_hot_news",  # 把右边计算出来的结果保存到 name 变量中，方便后面的代码继续复用
    queue="statistics"  # 把右边计算出来的结果保存到 queue 变量中，方便后面的代码继续复用
)  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
def refresh_hot_news():  # 定义函数 refresh_hot_news，把一段可以复用的逻辑单独封装起来
    """定时刷新热门新闻榜单"""
    try:  # 开始尝试执行可能出错的逻辑，如果报错就会转到下面的异常分支
        logger.info("刷新热门新闻榜单")  # 记录一条日志，方便后续排查程序运行过程和定位问题
        return {"code": 200, "msg": "热榜刷新成功"}  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
    except Exception as e:  # 如果上面 try 里的代码报错，就进入这个异常处理分支
        logger.error(f"热榜刷新失败 | 错误={str(e)}")  # 记录一条日志，方便后续排查程序运行过程和定位问题
        raise  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行


@celery_app.task(  # 使用 celery_app.task 装饰下面的函数或类，给它附加额外能力
    name="tasks.statistics_tasks.collect_user_behavior",  # 把右边计算出来的结果保存到 name 变量中，方便后面的代码继续复用
    queue="statistics",  # 把右边计算出来的结果保存到 queue 变量中，方便后面的代码继续复用
    rate_limit="500/m"  # 把右边计算出来的结果保存到 rate_limit 变量中，方便后面的代码继续复用
)  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
def collect_user_behavior(user_id: int, action: str, news_id: int):  # 定义函数 collect_user_behavior，把一段可以复用的逻辑单独封装起来
    """收集用户行为：查看/点赞/分享/收藏"""
    try:  # 开始尝试执行可能出错的逻辑，如果报错就会转到下面的异常分支
        logger.info(f"收集用户行为 | user_id={user_id}, 行为={action}, news_id={news_id}")  # 记录一条日志，方便后续排查程序运行过程和定位问题
        return {"code": 200, "msg": "行为收集成功"}  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
    except Exception as e:  # 如果上面 try 里的代码报错，就进入这个异常处理分支
        logger.error(f"行为收集失败 | 错误={str(e)}")  # 记录一条日志，方便后续排查程序运行过程和定位问题
        raise  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行