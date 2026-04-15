# -*- coding: utf-8 -*-
"""向量库服务。"""

from __future__ import annotations

from pathlib import Path
from threading import Lock
from typing import Any, Optional

from langchain_core.documents import Document
from starlette.concurrency import run_in_threadpool

try:
    from langchain_chroma import Chroma
except ImportError:  # pragma: no cover - 兼容旧依赖组合
    from langchain_community.vectorstores import Chroma

from rag.embeddings import get_embedding_service
from utils.logger import get_logger

logger = get_logger(name="VectorStore")

CHROMA_PERSIST_DIR = str(Path(__file__).parent.parent / "data" / "chroma")
COLLECTION_NAME = "news_collection"


def _normalize_category_id(category_id: Any) -> str:
    """统一 metadata 中 `category_id` 的类型。

    Chroma 过滤条件对类型比较敏感，因此这里统一写入字符串，读取时也按字符串过滤。
    """

    return str(category_id) if category_id is not None else "0"


class VectorStoreService:
    """统一管理 Chroma 生命周期与操作。"""

    def __init__(self) -> None:
        """初始化向量库服务的懒加载状态。"""
        self._vectorstore: Optional[Chroma] = None
        self._lock = Lock()

    def _build_sync(self) -> Chroma:
        """同步创建 Chroma 向量库实例。"""
        Path(CHROMA_PERSIST_DIR).mkdir(parents=True, exist_ok=True)
        embeddings = get_embedding_service().get_embeddings()
        logger.info("初始化 Chroma 向量库", persist_directory=CHROMA_PERSIST_DIR)
        return Chroma(
            persist_directory=CHROMA_PERSIST_DIR,
            embedding_function=embeddings,
            collection_name=COLLECTION_NAME,
        )

    def get_vectorstore(self) -> Chroma:
        """同步获取向量库实例。"""

        if self._vectorstore is not None:
            return self._vectorstore

        with self._lock:
            if self._vectorstore is None:
                self._vectorstore = self._build_sync()
        return self._vectorstore

    async def ensure_ready(self) -> Chroma:
        """异步预热向量库。"""

        if self._vectorstore is not None:
            return self._vectorstore
        await run_in_threadpool(self.get_vectorstore)
        return self.get_vectorstore()

    def add_news(self, news_list: list[dict[str, Any]]) -> int:
        """批量写入新闻向量。"""

        if not news_list:
            return 0

        vectorstore = self.get_vectorstore()
        texts: list[str] = []
        metadatas: list[dict[str, Any]] = []
        ids: list[str] = []

        for news in news_list:
            news_id = news.get("id")
            title = news.get("title")
            if not news_id or not title:
                logger.warning("跳过缺少关键字段的新闻", news=news)
                continue

            content = (news.get("content") or "")[:1000]
            texts.append(f"标题：{title}\n内容：{content}")
            ids.append(str(news_id))
            metadatas.append(
                {
                    "news_id": str(news_id),
                    "title": title,
                    "category_id": _normalize_category_id(news.get("category_id")),
                }
            )

        if not texts:
            return 0

        # 通过显式 id 覆盖旧文档，避免重复构建索引时产生多份脏数据。
        try:
            vectorstore.delete(ids=ids)
        except Exception:
            logger.debug("删除旧向量失败，继续尝试新增", ids=ids, exc_info=True)

        vectorstore.add_texts(texts=texts, metadatas=metadatas, ids=ids)
        return len(texts)

    async def asearch(
        self,
        query: str,
        top_k: int = 5,
        category_id: Optional[int | str] = None,
    ) -> list[Document]:
        """异步向量检索。

        同步的 Chroma 检索会走线程池，避免阻塞 async 接口。
        """

        await self.ensure_ready()
        return await run_in_threadpool(self.search, query, top_k, category_id)

    def search(
        self,
        query: str,
        top_k: int = 5,
        category_id: Optional[int | str] = None,
    ) -> list[Document]:
        """同步向量检索。"""

        vectorstore = self.get_vectorstore()
        filter_dict = None
        if category_id is not None:
            filter_dict = {"category_id": _normalize_category_id(category_id)}
        return vectorstore.similarity_search(query=query, k=top_k, filter=filter_dict)

    def delete_news(self, news_ids: list[int]) -> int:
        """按新闻 ID 删除向量。"""

        if not news_ids:
            return 0

        ids = [str(news_id) for news_id in news_ids]
        vectorstore = self.get_vectorstore()
        existing = vectorstore.get(ids=ids, include=[])
        existing_ids = existing.get("ids", []) if isinstance(existing, dict) else []
        if not existing_ids:
            return 0

        vectorstore.delete(ids=list(existing_ids))
        return len(existing_ids)

    def count(self) -> int:
        """返回向量总数。

        这里使用公开的 `get()` 接口而不是私有 `_collection`。
        """

        vectorstore = self.get_vectorstore()
        data = vectorstore.get(include=[])
        ids = data.get("ids", []) if isinstance(data, dict) else []
        return len(ids)

    def stats(self) -> dict[str, Any]:
        """返回当前向量库的基础统计信息。"""
        return {
            "total_vectors": self.count(),
            "persist_directory": CHROMA_PERSIST_DIR,
        }

    def reset(self) -> None:
        """清理内存中的向量库实例。

        这个方法主要给重建索引或测试场景使用。
        """

        with self._lock:
            self._vectorstore = None


_vectorstore_service: Optional[VectorStoreService] = None


def get_vectorstore_service() -> VectorStoreService:
    """返回向量库服务的全局单例。"""
    global _vectorstore_service
    if _vectorstore_service is None:
        _vectorstore_service = VectorStoreService()
    return _vectorstore_service


def get_vectorstore() -> Chroma:
    """兼容旧接口。"""

    return get_vectorstore_service().get_vectorstore()


async def preload_vectorstore() -> Chroma:
    """启动期可选预热。"""

    return await get_vectorstore_service().ensure_ready()


def add_news_to_vectorstore(news_list: list[dict[str, Any]]) -> int:
    """兼容旧接口，批量把新闻写入向量库。"""
    return get_vectorstore_service().add_news(news_list)


def search_similar_news(
    query: str,
    top_k: int = 5,
    category_id: Optional[int] = None,
) -> list[Document]:
    """兼容旧接口，根据查询语句检索相似新闻。"""
    return get_vectorstore_service().search(query=query, top_k=top_k, category_id=category_id)


def delete_news_from_vectorstore(news_ids: list[int]) -> int:
    """兼容旧接口，按新闻 ID 删除向量。"""
    return get_vectorstore_service().delete_news(news_ids)


def get_vectorstore_stats() -> dict[str, Any]:
    """兼容旧接口，返回向量库统计信息。"""
    return get_vectorstore_service().stats()


def reset_vectorstore_service() -> None:
    """重置全局单例，供重建索引时使用。"""

    service = get_vectorstore_service()
    service.reset()
