# -*- coding: utf-8 -*-
"""新闻检索服务。

职责拆分：
- 向量库只负责语义召回。
- 本服务负责把召回结果补全成结构化新闻数据。
- 路由与 Agent 只消费最终结果，不再关心底层检索细节。
"""

from __future__ import annotations  # 开启延迟解析类型注解，避免前向引用在导入阶段就被过早求值

from typing import Any, Optional  # 从 typing 模块导入当前文件后续要用到的对象

from sqlalchemy import select  # 从 sqlalchemy 模块导入当前文件后续要用到的对象

from configs.db import AsyncSessionLocal  # 从 configs.db 模块导入当前文件后续要用到的对象
from models.news import News  # 从 models.news 模块导入当前文件后续要用到的对象
from rag.vectorstore import VectorStoreService, get_vectorstore_service  # 从 rag.vectorstore 模块导入当前文件后续要用到的对象
from utils.logger import get_logger  # 从 utils.logger 模块导入当前文件后续要用到的对象

logger = get_logger(name="NewsRetriever")  # 把右边计算出来的结果保存到 logger 变量中，方便后面的代码继续复用

CATEGORY_ID_MAP = {  # 把这个常量值保存到 CATEGORY_ID_MAP 中，后面会作为固定配置反复使用
    "头条": 1,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    "社会": 2,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    "国内": 3,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    "国际": 4,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    "娱乐": 5,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    "体育": 6,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    "科技": 7,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    "财经": 8,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
}  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级


def _serialize_news(news: News) -> dict[str, Any]:  # 定义函数 _serialize_news，把一段可以复用的逻辑单独封装起来
    """统一新闻输出格式。"""

    return {  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
        "id": news.id,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        "title": news.title,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        "content": news.content,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        "description": news.description,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        "category_id": news.category_id,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        "publish_time": news.publish_time.isoformat() if news.publish_time else None,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        "image": news.image,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        "author": news.author,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    }  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级


class NewsRetrieverService:  # 定义 NewsRetrieverService 类，用来把这一块相关的状态和行为组织在一起
    """组合向量检索与数据库补全的服务层。"""

    def __init__(  # 定义函数 __init__，把一段可以复用的逻辑单独封装起来
        self,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        vectorstore_service: Optional[VectorStoreService] = None,  # 把右边计算出来的结果保存到 vectorstore_service 变量中，方便后面的代码继续复用
    ) -> None:  # 这一行开始一个新的代码块，下面缩进的内容都属于它
        """初始化检索服务，可按需注入向量库依赖。"""
        self.vectorstore_service = vectorstore_service or get_vectorstore_service()  # 把右边计算出来的结果保存到 vectorstore_service 变量中，方便后面的代码继续复用

    async def search_news(  # 定义异步函数 search_news，调用它时通常需要配合 await 使用
        self,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        query: str,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        category: Optional[str] = None,  # 把右边计算出来的结果保存到 category 变量中，方便后面的代码继续复用
        top_k: int = 5,  # 把右边计算出来的结果保存到 top_k 变量中，方便后面的代码继续复用
    ) -> list[dict[str, Any]]:  # 这一行开始一个新的代码块，下面缩进的内容都属于它
        """优先走语义检索，再用数据库补齐详情。"""

        query = (query or "").strip()  # 把右边计算出来的结果保存到 query 变量中，方便后面的代码继续复用
        if not query:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            return []  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

        category_id = CATEGORY_ID_MAP.get(category) if category else None  # 把右边计算出来的结果保存到 category_id 变量中，方便后面的代码继续复用
        logger.info("开始检索新闻", query=query, category=category, top_k=top_k)  # 记录一条日志，方便后续排查程序运行过程和定位问题

        docs = await self.vectorstore_service.asearch(  # 把右边计算出来的结果保存到 docs 变量中，方便后面的代码继续复用
            query=query,  # 把右边计算出来的结果保存到 query 变量中，方便后面的代码继续复用
            top_k=max(top_k * 2, top_k),  # 把右边计算出来的结果保存到 top_k 变量中，方便后面的代码继续复用
            category_id=category_id,  # 把右边计算出来的结果保存到 category_id 变量中，方便后面的代码继续复用
        )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级

        news_ids: list[int] = []  # 把右边计算出来的结果保存到 news_ids 变量中，方便后面的代码继续复用
        seen_ids: set[int] = set()  # 把右边计算出来的结果保存到 seen_ids 变量中，方便后面的代码继续复用
        for doc in docs:  # 开始遍历可迭代对象里的每一项，并对每一项执行同样的处理
            raw_news_id = doc.metadata.get("news_id")  # 把右边计算出来的结果保存到 raw_news_id 变量中，方便后面的代码继续复用
            if raw_news_id is None:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                continue  # 跳过当前这一轮循环剩下的语句，直接开始下一轮
            try:  # 开始尝试执行可能出错的逻辑，如果报错就会转到下面的异常分支
                news_id = int(raw_news_id)  # 把右边计算出来的结果保存到 news_id 变量中，方便后面的代码继续复用
            except (TypeError, ValueError):  # 如果上面 try 里的代码报错，就进入这个异常处理分支
                continue  # 跳过当前这一轮循环剩下的语句，直接开始下一轮
            if news_id in seen_ids:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                continue  # 跳过当前这一轮循环剩下的语句，直接开始下一轮
            seen_ids.add(news_id)  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
            news_ids.append(news_id)  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行

        if not news_ids and category_id is not None:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            # 当向量召回为空时，按分类走一个结构化兜底，避免问“科技新闻”却直接返回空。
            return await self.search_news_by_category(category=category, limit=top_k)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

        if not news_ids:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            return []  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

        async with AsyncSessionLocal() as db:  # 以异步上下文管理的方式使用资源，结束时会自动做清理
            result = await db.execute(select(News).where(News.id.in_(news_ids)))  # 把右边计算出来的结果保存到 result 变量中，方便后面的代码继续复用
            news_list = result.scalars().all()  # 把右边计算出来的结果保存到 news_list 变量中，方便后面的代码继续复用

        news_map = {news.id: news for news in news_list}  # 把右边计算出来的结果保存到 news_map 变量中，方便后面的代码继续复用
        results = [_serialize_news(news_map[news_id]) for news_id in news_ids if news_id in news_map]  # 把右边计算出来的结果保存到 results 变量中，方便后面的代码继续复用
        return results[:top_k]  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    async def search_news_by_category(  # 定义异步函数 search_news_by_category，调用它时通常需要配合 await 使用
        self,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        category: str,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        limit: int = 10,  # 把右边计算出来的结果保存到 limit 变量中，方便后面的代码继续复用
    ) -> list[dict[str, Any]]:  # 这一行开始一个新的代码块，下面缩进的内容都属于它
        """按分类直接查询数据库。"""

        category_id = CATEGORY_ID_MAP.get(category)  # 把右边计算出来的结果保存到 category_id 变量中，方便后面的代码继续复用
        if category_id is None:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            return []  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

        async with AsyncSessionLocal() as db:  # 以异步上下文管理的方式使用资源，结束时会自动做清理
            result = await db.execute(  # 把右边计算出来的结果保存到 result 变量中，方便后面的代码继续复用
                select(News)  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                .where(News.category_id == category_id)  # 把右边计算出来的结果保存到 .where(News.category_id 变量中，方便后面的代码继续复用
                .order_by(News.publish_time.desc(), News.id.desc())  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                .limit(limit)  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
            )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
            rows = result.scalars().all()  # 把右边计算出来的结果保存到 rows 变量中，方便后面的代码继续复用

        return [_serialize_news(news) for news in rows]  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束


_news_retriever_service: Optional[NewsRetrieverService] = None  # 把右边计算出来的结果保存到 _news_retriever_service 变量中，方便后面的代码继续复用


def get_news_retriever_service() -> NewsRetrieverService:  # 定义函数 get_news_retriever_service，把一段可以复用的逻辑单独封装起来
    """返回新闻检索服务的全局单例。"""
    global _news_retriever_service  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    if _news_retriever_service is None:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
        _news_retriever_service = NewsRetrieverService()  # 把右边计算出来的结果保存到 _news_retriever_service 变量中，方便后面的代码继续复用
    return _news_retriever_service  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束


async def search_news(  # 定义异步函数 search_news，调用它时通常需要配合 await 使用
    query: str,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    category: Optional[str] = None,  # 把右边计算出来的结果保存到 category 变量中，方便后面的代码继续复用
    top_k: int = 5,  # 把右边计算出来的结果保存到 top_k 变量中，方便后面的代码继续复用
) -> list[dict[str, Any]]:  # 这一行开始一个新的代码块，下面缩进的内容都属于它
    """兼容旧接口。"""

    return await get_news_retriever_service().search_news(query=query, category=category, top_k=top_k)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束


async def search_news_by_category(  # 定义异步函数 search_news_by_category，调用它时通常需要配合 await 使用
    category: str,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    limit: int = 10,  # 把右边计算出来的结果保存到 limit 变量中，方便后面的代码继续复用
) -> list[dict[str, Any]]:  # 这一行开始一个新的代码块，下面缩进的内容都属于它
    """兼容旧接口，按分类直接查询新闻。"""
    return await get_news_retriever_service().search_news_by_category(category=category, limit=limit)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
