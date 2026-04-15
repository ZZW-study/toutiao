# -*- coding: utf-8 -*-
"""
新闻爬虫 Celery 定时任务

说明：
- 本模块将 `services.news_spider` 的异步抓取逻辑封装为 Celery 任务，方便定时执行与队列调度。
- 由于 Celery 任务函数为同步函数，这里在任务内部创建新的 asyncio 事件循环并运行异步函数，
    确保在 Celery worker（通常为同步环境）中能正确执行 async 代码。
- 任务会把抓取到的 `NewsItem` 列表交由 `crud.news_spider` 进行批量持久化，
    并在出错时按照 Celery 的重试策略（`max_retries` / `default_retry_delay`）处理。

注意事项：
- 任务内部不要直接抛出未捕获的异常，需使用 `self.retry` 以触发重试逻辑。
- 对外部请求（HTTP/第三方 API）应有超时与异常处理，避免阻塞 worker。
"""

from middlewares.celery import celery_app  # 从 middlewares.celery 模块导入当前文件后续要用到的对象
from services.news_spider import NewsSpiderService  # 从 services.news_spider 模块导入当前文件后续要用到的对象
from crud.news_spider import NewsSpiderCRUD  # 从 crud.news_spider 模块导入当前文件后续要用到的对象
from configs.db import AsyncSessionLocal  # 从 configs.db 模块导入当前文件后续要用到的对象
from utils.logger import get_logger  # 从 utils.logger 模块导入当前文件后续要用到的对象

logger = get_logger(name="NewsSpiderTasks")  # 把右边计算出来的结果保存到 logger 变量中，方便后面的代码继续复用

# 日志记录器已初始化：用于任务运行时记录抓取/持久化过程中的信息与错误。


@celery_app.task(  # 使用 celery_app.task 装饰下面的函数或类，给它附加额外能力
    name="tasks.news_spider_tasks.fetch_and_save_news",  # 把右边计算出来的结果保存到 name 变量中，方便后面的代码继续复用
    queue="news",  # 把右边计算出来的结果保存到 queue 变量中，方便后面的代码继续复用
    bind=True,  # 把右边计算出来的结果保存到 bind 变量中，方便后面的代码继续复用
    max_retries=3,  # 把右边计算出来的结果保存到 max_retries 变量中，方便后面的代码继续复用
    default_retry_delay=300  # 把右边计算出来的结果保存到 default_retry_delay 变量中，方便后面的代码继续复用
)  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
def fetch_and_save_news(self):  # 定义函数 fetch_and_save_news，把一段可以复用的逻辑单独封装起来
    """
    定时抓取新闻并保存到数据库
    每6小时执行一次（可在 celery_conf.py 中配置）
    """
    # 将 asyncio 在任务内部导入，避免在模块导入时引入异步运行时，
    # 这有助于在 Celery worker（通常为同步进程）中保持兼容性。
    import asyncio  # 导入 asyncio 模块，给当前文件后面的逻辑使用
    import asyncio  # 导入 asyncio 模块，给当前文件后面的逻辑使用

    async def _execute():  # 定义异步函数 _execute，调用它时通常需要配合 await 使用
        """异步执行抓取与入库逻辑的内部函数（在新事件循环中运行）。"""
        # 在异步上下文中创建数据库会话，确保会话正确提交/回滚并关闭连接
        async with AsyncSessionLocal() as db:  # 以异步上下文管理的方式使用资源，结束时会自动做清理
            try:  # 开始尝试执行可能出错的逻辑，如果报错就会转到下面的异常分支
                # 确保分类表有基础数据，避免后续入库因为外键或分类缺失而失败
                await NewsSpiderCRUD.ensure_categories(db)  # 等待这个异步操作完成，再继续执行后面的代码

                # 并发抓取所有配置的新闻源（Sina / QQ / 其他），由服务层负责并发控制与限流
                news_list = await NewsSpiderService.fetch_all_news()  # 把右边计算出来的结果保存到 news_list 变量中，方便后面的代码继续复用

                # 若无抓取结果，记录警告并返回成功状态（无需重试）
                if not news_list:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                    logger.warning("本次抓取未获取到任何新闻")  # 记录一条日志，方便后续排查程序运行过程和定位问题
                    return {"status": "success", "saved": 0}  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

                # 批量保存抓取结果，并由 CRUD 层返回统计信息（如 saved/updated/duplicated）
                result = await NewsSpiderCRUD.save_news_batch(db, news_list)  # 把右边计算出来的结果保存到 result 变量中，方便后面的代码继续复用
                logger.info(f"新闻爬取任务完成: {result}")  # 记录一条日志，方便后续排查程序运行过程和定位问题
                return {"status": "success", **result}  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

            except Exception as e:  # 如果上面 try 里的代码报错，就进入这个异常处理分支
                # 捕获任意异常并使用 Celery 的重试机制重新调度任务，避免 worker 崩溃
                logger.error(f"新闻爬取任务失败: {str(e)}")  # 记录一条日志，方便后续排查程序运行过程和定位问题
                # 使用绑定任务的 self.retry 触发重试，并把原始异常传入
                raise self.retry(exc=e)  # 主动抛出异常，让上层知道这里出现了需要处理的问题

    # 在 Celery 同步环境中运行异步代码：为安全起见创建新的事件循环
    # 创建独立事件循环并设置为当前线程的事件循环，避免与 Celery 的全局/其他任务冲突
    loop = asyncio.new_event_loop()  # 把右边计算出来的结果保存到 loop 变量中，方便后面的代码继续复用
    asyncio.set_event_loop(loop)  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    try:  # 开始尝试执行可能出错的逻辑，如果报错就会转到下面的异常分支
        # 在新事件循环中同步运行异步函数，返回异步执行结果
        return loop.run_until_complete(_execute())  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
    finally:  # 无论前面的逻辑是否成功，这个收尾分支最终都会执行
        # 及时关闭事件循环释放资源
        loop.close()  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行


@celery_app.task(  # 使用 celery_app.task 装饰下面的函数或类，给它附加额外能力
    name="tasks.news_spider_tasks.fetch_sina_news",  # 把右边计算出来的结果保存到 name 变量中，方便后面的代码继续复用
    queue="news"  # 把右边计算出来的结果保存到 queue 变量中，方便后面的代码继续复用
)  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
def fetch_sina_news():  # 定义函数 fetch_sina_news，把一段可以复用的逻辑单独封装起来
    """单独抓取新浪新闻"""
    # 在任务内部导入 asyncio，按需创建事件循环执行异步函数
    import asyncio  # 导入 asyncio 模块，给当前文件后面的逻辑使用
    import asyncio  # 导入 asyncio 模块，给当前文件后面的逻辑使用

    async def _execute():  # 定义异步函数 _execute，调用它时通常需要配合 await 使用
        """抓取新浪新闻并入库的异步内部函数。"""
        # 在异步上下文中完成抓取与持久化；出错时返回错误信息（不自动 retry）
        async with AsyncSessionLocal() as db:  # 以异步上下文管理的方式使用资源，结束时会自动做清理
            try:  # 开始尝试执行可能出错的逻辑，如果报错就会转到下面的异常分支
                news_list = await NewsSpiderService.fetch_sina_news()  # 把右边计算出来的结果保存到 news_list 变量中，方便后面的代码继续复用
                if not news_list:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                    return {"status": "success", "saved": 0}  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
                result = await NewsSpiderCRUD.save_news_batch(db, news_list)  # 把右边计算出来的结果保存到 result 变量中，方便后面的代码继续复用
                return {"status": "success", **result}  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
            except Exception as e:  # 如果上面 try 里的代码报错，就进入这个异常处理分支
                # 此处记录错误并返回错误信息，调用方可根据返回值或监控采取措施
                logger.error(f"新浪新闻爬取失败: {str(e)}")  # 记录一条日志，方便后续排查程序运行过程和定位问题
                return {"status": "error", "message": str(e)}  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    loop = asyncio.new_event_loop()  # 把右边计算出来的结果保存到 loop 变量中，方便后面的代码继续复用
    asyncio.set_event_loop(loop)  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    try:  # 开始尝试执行可能出错的逻辑，如果报错就会转到下面的异常分支
        return loop.run_until_complete(_execute())  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
    finally:  # 无论前面的逻辑是否成功，这个收尾分支最终都会执行
        loop.close()  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行


@celery_app.task(  # 使用 celery_app.task 装饰下面的函数或类，给它附加额外能力
    name="tasks.news_spider_tasks.fetch_qq_news",  # 把右边计算出来的结果保存到 name 变量中，方便后面的代码继续复用
    queue="news"  # 把右边计算出来的结果保存到 queue 变量中，方便后面的代码继续复用
)  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
def fetch_qq_news():  # 定义函数 fetch_qq_news，把一段可以复用的逻辑单独封装起来
    """单独抓取腾讯新闻"""
    # 按与 Sina 相同的模式，在任务内部创建事件循环并执行异步抓取
    import asyncio  # 导入 asyncio 模块，给当前文件后面的逻辑使用
    import asyncio  # 导入 asyncio 模块，给当前文件后面的逻辑使用

    async def _execute():  # 定义异步函数 _execute，调用它时通常需要配合 await 使用
        """抓取腾讯新闻并入库的异步内部函数。"""
        async with AsyncSessionLocal() as db:  # 以异步上下文管理的方式使用资源，结束时会自动做清理
            try:  # 开始尝试执行可能出错的逻辑，如果报错就会转到下面的异常分支
                news_list = await NewsSpiderService.fetch_qq_news()  # 把右边计算出来的结果保存到 news_list 变量中，方便后面的代码继续复用
                if not news_list:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                    return {"status": "success", "saved": 0}  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
                result = await NewsSpiderCRUD.save_news_batch(db, news_list)  # 把右边计算出来的结果保存到 result 变量中，方便后面的代码继续复用
                return {"status": "success", **result}  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
            except Exception as e:  # 如果上面 try 里的代码报错，就进入这个异常处理分支
                logger.error(f"腾讯新闻爬取失败: {str(e)}")  # 记录一条日志，方便后续排查程序运行过程和定位问题
                return {"status": "error", "message": str(e)}  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    loop = asyncio.new_event_loop()  # 把右边计算出来的结果保存到 loop 变量中，方便后面的代码继续复用
    asyncio.set_event_loop(loop)  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    try:  # 开始尝试执行可能出错的逻辑，如果报错就会转到下面的异常分支
        return loop.run_until_complete(_execute())  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
    finally:  # 无论前面的逻辑是否成功，这个收尾分支最终都会执行
        loop.close()  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
