# -*- coding: utf-8 -*-
"""向量库服务。"""

from __future__ import annotations  # 开启延迟解析类型注解，避免前向引用在导入阶段就被过早求值

from pathlib import Path  # 从 pathlib 模块导入当前文件后续要用到的对象
from threading import Lock  # 从 threading 模块导入当前文件后续要用到的对象
from typing import Any, Optional  # 从 typing 模块导入当前文件后续要用到的对象

from langchain_core.documents import Document  # 从 langchain_core.documents 模块导入当前文件后续要用到的对象
from starlette.concurrency import run_in_threadpool  # 从 starlette.concurrency 模块导入当前文件后续要用到的对象

try:  # 开始尝试执行可能出错的逻辑，如果报错就会转到下面的异常分支
    from langchain_chroma import Chroma  # 从 langchain_chroma 模块导入当前文件后续要用到的对象
except ImportError:  # pragma: no cover - 兼容旧依赖组合
    from langchain_community.vectorstores import Chroma  # 从 langchain_community.vectorstores 模块导入当前文件后续要用到的对象

from rag.embeddings import get_embedding_service  # 从 rag.embeddings 模块导入当前文件后续要用到的对象
from utils.logger import get_logger  # 从 utils.logger 模块导入当前文件后续要用到的对象

logger = get_logger(name="VectorStore")  # 把右边计算出来的结果保存到 logger 变量中，方便后面的代码继续复用

CHROMA_PERSIST_DIR = str(Path(__file__).parent.parent / "data" / "chroma")  # 把这个常量值保存到 CHROMA_PERSIST_DIR 中，后面会作为固定配置反复使用
COLLECTION_NAME = "news_collection"  # 把这个常量值保存到 COLLECTION_NAME 中，后面会作为固定配置反复使用


def _normalize_category_id(category_id: Any) -> str:  # 定义函数 _normalize_category_id，把一段可以复用的逻辑单独封装起来
    """统一 metadata 中 `category_id` 的类型。

    Chroma 过滤条件对类型比较敏感，因此这里统一写入字符串，读取时也按字符串过滤。
    """

    return str(category_id) if category_id is not None else "0"  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束


class VectorStoreService:  # 定义 VectorStoreService 类，用来把这一块相关的状态和行为组织在一起
    """统一管理 Chroma 生命周期与操作。"""

    def __init__(self) -> None:  # 定义函数 __init__，把一段可以复用的逻辑单独封装起来
        """初始化向量库服务的懒加载状态。"""
        self._vectorstore: Optional[Chroma] = None  # 把右边计算出来的结果保存到 _vectorstore 变量中，方便后面的代码继续复用
        self._lock = Lock()  # 把右边计算出来的结果保存到 _lock 变量中，方便后面的代码继续复用

    def _build_sync(self) -> Chroma:  # 定义函数 _build_sync，把一段可以复用的逻辑单独封装起来
        """同步创建 Chroma 向量库实例。"""
        Path(CHROMA_PERSIST_DIR).mkdir(parents=True, exist_ok=True)  # 把右边计算出来的结果保存到 Path(CHROMA_PERSIST_DIR).mkdir(parents 变量中，方便后面的代码继续复用
        embeddings = get_embedding_service().get_embeddings()  # 把右边计算出来的结果保存到 embeddings 变量中，方便后面的代码继续复用
        logger.info("初始化 Chroma 向量库", persist_directory=CHROMA_PERSIST_DIR)  # 记录一条日志，方便后续排查程序运行过程和定位问题
        return Chroma(  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
            persist_directory=CHROMA_PERSIST_DIR,  # 把右边计算出来的结果保存到 persist_directory 变量中，方便后面的代码继续复用
            embedding_function=embeddings,  # 把右边计算出来的结果保存到 embedding_function 变量中，方便后面的代码继续复用
            collection_name=COLLECTION_NAME,  # 把右边计算出来的结果保存到 collection_name 变量中，方便后面的代码继续复用
        )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级

    def get_vectorstore(self) -> Chroma:  # 定义函数 get_vectorstore，把一段可以复用的逻辑单独封装起来
        """同步获取向量库实例。"""

        if self._vectorstore is not None:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            return self._vectorstore  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

        with self._lock:  # 以上下文管理的方式使用资源，离开代码块时会自动释放或关闭
            if self._vectorstore is None:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                self._vectorstore = self._build_sync()  # 把右边计算出来的结果保存到 _vectorstore 变量中，方便后面的代码继续复用
        return self._vectorstore  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    async def ensure_ready(self) -> Chroma:  # 定义异步函数 ensure_ready，调用它时通常需要配合 await 使用
        """异步预热向量库。"""

        if self._vectorstore is not None:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            return self._vectorstore  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
        await run_in_threadpool(self.get_vectorstore)  # 等待这个异步操作完成，再继续执行后面的代码
        return self.get_vectorstore()  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    def add_news(self, news_list: list[dict[str, Any]]) -> int:  # 定义函数 add_news，把一段可以复用的逻辑单独封装起来
        """批量写入新闻向量。"""

        if not news_list:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            return 0  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

        vectorstore = self.get_vectorstore()  # 把右边计算出来的结果保存到 vectorstore 变量中，方便后面的代码继续复用
        texts: list[str] = []  # 把右边计算出来的结果保存到 texts 变量中，方便后面的代码继续复用
        metadatas: list[dict[str, Any]] = []  # 把右边计算出来的结果保存到 metadatas 变量中，方便后面的代码继续复用
        ids: list[str] = []  # 把右边计算出来的结果保存到 ids 变量中，方便后面的代码继续复用

        for news in news_list:  # 开始遍历可迭代对象里的每一项，并对每一项执行同样的处理
            news_id = news.get("id")  # 把右边计算出来的结果保存到 news_id 变量中，方便后面的代码继续复用
            title = news.get("title")  # 把右边计算出来的结果保存到 title 变量中，方便后面的代码继续复用
            if not news_id or not title:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                logger.warning("跳过缺少关键字段的新闻", news=news)  # 记录一条日志，方便后续排查程序运行过程和定位问题
                continue  # 跳过当前这一轮循环剩下的语句，直接开始下一轮

            content = (news.get("content") or "")[:1000]  # 把右边计算出来的结果保存到 content 变量中，方便后面的代码继续复用
            texts.append(f"标题：{title}\n内容：{content}")  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
            ids.append(str(news_id))  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
            metadatas.append(  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                {  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                    "news_id": str(news_id),  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                    "title": title,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                    "category_id": _normalize_category_id(news.get("category_id")),  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
                }  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
            )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级

        if not texts:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            return 0  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

        # 通过显式 id 覆盖旧文档，避免重复构建索引时产生多份脏数据。
        try:  # 开始尝试执行可能出错的逻辑，如果报错就会转到下面的异常分支
            vectorstore.delete(ids=ids)  # 把右边计算出来的结果保存到 vectorstore.delete(ids 变量中，方便后面的代码继续复用
        except Exception:  # 如果上面 try 里的代码报错，就进入这个异常处理分支
            logger.debug("删除旧向量失败，继续尝试新增", ids=ids, exc_info=True)  # 记录一条日志，方便后续排查程序运行过程和定位问题

        vectorstore.add_texts(texts=texts, metadatas=metadatas, ids=ids)  # 把右边计算出来的结果保存到 vectorstore.add_texts(texts 变量中，方便后面的代码继续复用
        return len(texts)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    async def asearch(  # 定义异步函数 asearch，调用它时通常需要配合 await 使用
        self,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        query: str,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        top_k: int = 5,  # 把右边计算出来的结果保存到 top_k 变量中，方便后面的代码继续复用
        category_id: Optional[int | str] = None,  # 把右边计算出来的结果保存到 category_id 变量中，方便后面的代码继续复用
    ) -> list[Document]:  # 这一行开始一个新的代码块，下面缩进的内容都属于它
        """异步向量检索。

        同步的 Chroma 检索会走线程池，避免阻塞 async 接口。
        """

        await self.ensure_ready()  # 等待这个异步操作完成，再继续执行后面的代码
        return await run_in_threadpool(self.search, query, top_k, category_id)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    def search(  # 定义函数 search，把一段可以复用的逻辑单独封装起来
        self,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        query: str,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        top_k: int = 5,  # 把右边计算出来的结果保存到 top_k 变量中，方便后面的代码继续复用
        category_id: Optional[int | str] = None,  # 把右边计算出来的结果保存到 category_id 变量中，方便后面的代码继续复用
    ) -> list[Document]:  # 这一行开始一个新的代码块，下面缩进的内容都属于它
        """同步向量检索。"""

        vectorstore = self.get_vectorstore()  # 把右边计算出来的结果保存到 vectorstore 变量中，方便后面的代码继续复用
        filter_dict = None  # 把右边计算出来的结果保存到 filter_dict 变量中，方便后面的代码继续复用
        if category_id is not None:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            filter_dict = {"category_id": _normalize_category_id(category_id)}  # 把右边计算出来的结果保存到 filter_dict 变量中，方便后面的代码继续复用
        return vectorstore.similarity_search(query=query, k=top_k, filter=filter_dict)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    def delete_news(self, news_ids: list[int]) -> int:  # 定义函数 delete_news，把一段可以复用的逻辑单独封装起来
        """按新闻 ID 删除向量。"""

        if not news_ids:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            return 0  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

        ids = [str(news_id) for news_id in news_ids]  # 把右边计算出来的结果保存到 ids 变量中，方便后面的代码继续复用
        vectorstore = self.get_vectorstore()  # 把右边计算出来的结果保存到 vectorstore 变量中，方便后面的代码继续复用
        existing = vectorstore.get(ids=ids, include=[])  # 把右边计算出来的结果保存到 existing 变量中，方便后面的代码继续复用
        existing_ids = existing.get("ids", []) if isinstance(existing, dict) else []  # 把右边计算出来的结果保存到 existing_ids 变量中，方便后面的代码继续复用
        if not existing_ids:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            return 0  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

        vectorstore.delete(ids=list(existing_ids))  # 把右边计算出来的结果保存到 vectorstore.delete(ids 变量中，方便后面的代码继续复用
        return len(existing_ids)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    def count(self) -> int:  # 定义函数 count，把一段可以复用的逻辑单独封装起来
        """返回向量总数。

        这里使用公开的 `get()` 接口而不是私有 `_collection`。
        """

        vectorstore = self.get_vectorstore()  # 把右边计算出来的结果保存到 vectorstore 变量中，方便后面的代码继续复用
        data = vectorstore.get(include=[])  # 把右边计算出来的结果保存到 data 变量中，方便后面的代码继续复用
        ids = data.get("ids", []) if isinstance(data, dict) else []  # 把右边计算出来的结果保存到 ids 变量中，方便后面的代码继续复用
        return len(ids)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    def stats(self) -> dict[str, Any]:  # 定义函数 stats，把一段可以复用的逻辑单独封装起来
        """返回当前向量库的基础统计信息。"""
        return {  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
            "total_vectors": self.count(),  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
            "persist_directory": CHROMA_PERSIST_DIR,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
        }  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级

    def reset(self) -> None:  # 定义函数 reset，把一段可以复用的逻辑单独封装起来
        """清理内存中的向量库实例。

        这个方法主要给重建索引或测试场景使用。
        """

        with self._lock:  # 以上下文管理的方式使用资源，离开代码块时会自动释放或关闭
            self._vectorstore = None  # 把右边计算出来的结果保存到 _vectorstore 变量中，方便后面的代码继续复用


_vectorstore_service: Optional[VectorStoreService] = None  # 把右边计算出来的结果保存到 _vectorstore_service 变量中，方便后面的代码继续复用


def get_vectorstore_service() -> VectorStoreService:  # 定义函数 get_vectorstore_service，把一段可以复用的逻辑单独封装起来
    """返回向量库服务的全局单例。"""
    global _vectorstore_service  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    if _vectorstore_service is None:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
        _vectorstore_service = VectorStoreService()  # 把右边计算出来的结果保存到 _vectorstore_service 变量中，方便后面的代码继续复用
    return _vectorstore_service  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束


def get_vectorstore() -> Chroma:  # 定义函数 get_vectorstore，把一段可以复用的逻辑单独封装起来
    """兼容旧接口。"""

    return get_vectorstore_service().get_vectorstore()  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束


async def preload_vectorstore() -> Chroma:  # 定义异步函数 preload_vectorstore，调用它时通常需要配合 await 使用
    """启动期可选预热。"""

    return await get_vectorstore_service().ensure_ready()  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束


def add_news_to_vectorstore(news_list: list[dict[str, Any]]) -> int:  # 定义函数 add_news_to_vectorstore，把一段可以复用的逻辑单独封装起来
    """兼容旧接口，批量把新闻写入向量库。"""
    return get_vectorstore_service().add_news(news_list)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束


def search_similar_news(  # 定义函数 search_similar_news，把一段可以复用的逻辑单独封装起来
    query: str,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    top_k: int = 5,  # 把右边计算出来的结果保存到 top_k 变量中，方便后面的代码继续复用
    category_id: Optional[int] = None,  # 把右边计算出来的结果保存到 category_id 变量中，方便后面的代码继续复用
) -> list[Document]:  # 这一行开始一个新的代码块，下面缩进的内容都属于它
    """兼容旧接口，根据查询语句检索相似新闻。"""
    return get_vectorstore_service().search(query=query, top_k=top_k, category_id=category_id)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束


def delete_news_from_vectorstore(news_ids: list[int]) -> int:  # 定义函数 delete_news_from_vectorstore，把一段可以复用的逻辑单独封装起来
    """兼容旧接口，按新闻 ID 删除向量。"""
    return get_vectorstore_service().delete_news(news_ids)  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束


def get_vectorstore_stats() -> dict[str, Any]:  # 定义函数 get_vectorstore_stats，把一段可以复用的逻辑单独封装起来
    """兼容旧接口，返回向量库统计信息。"""
    return get_vectorstore_service().stats()  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束


def reset_vectorstore_service() -> None:  # 定义函数 reset_vectorstore_service，把一段可以复用的逻辑单独封装起来
    """重置全局单例，供重建索引时使用。"""

    service = get_vectorstore_service()  # 把右边计算出来的结果保存到 service 变量中，方便后面的代码继续复用
    service.reset()  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
