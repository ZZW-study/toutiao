# -*- coding: utf-8 -*-
"""Embedding 服务。

这里不再在模块导入时直接加载模型，而是改成显式的服务类 + 惰性初始化。
这样可以避免：
- 导入路由时首屏卡住。
- 测试环境一 import `main` 就尝试加载大模型。
"""

from __future__ import annotations

from pathlib import Path
from threading import Lock
from typing import Optional

from starlette.concurrency import run_in_threadpool

try:
    from langchain_huggingface import HuggingFaceEmbeddings
except ImportError:  # pragma: no cover - 兼容旧依赖组合
    from langchain_community.embeddings import HuggingFaceEmbeddings

from utils.logger import get_logger

logger = get_logger(name="Embeddings")

EMBEDDING_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
MODEL_CACHE_DIR = Path(__file__).parent.parent / "data" / "embedding_model"
EMBEDDING_DIMENSION = 384


class EmbeddingService:
    """统一管理 embedding 模型的生命周期。"""

    def __init__(self) -> None:
        """初始化 embedding 服务的懒加载状态。"""
        self._instance: Optional[HuggingFaceEmbeddings] = None
        self._lock = Lock()

    def _build_sync(self) -> HuggingFaceEmbeddings:
        """同步加载 HuggingFace embedding 模型实例。"""
        Path.mkdir(MODEL_CACHE_DIR, exist_ok=True, parents=True)
        logger.info("开始加载 Embedding 模型", model=EMBEDDING_MODEL_NAME)
        embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL_NAME,
            cache_folder=str(MODEL_CACHE_DIR),
            model_kwargs={"device": "cpu"},
            encode_kwargs={"normalize_embeddings": True},
        )
        logger.info("Embedding 模型加载完成")
        return embeddings

    def get_embeddings(self) -> HuggingFaceEmbeddings:
        """同步获取模型实例。"""

        if self._instance is not None:
            return self._instance

        with self._lock:
            if self._instance is None:
                self._instance = self._build_sync()
        return self._instance

    async def aget_embeddings(self) -> HuggingFaceEmbeddings:
        """异步获取模型实例。

        重型初始化放到线程池中，避免阻塞 FastAPI 事件循环。
        """

        if self._instance is not None:
            return self._instance

        await run_in_threadpool(self.get_embeddings)
        return self.get_embeddings()


_embedding_service: Optional[EmbeddingService] = None


def get_embedding_service() -> EmbeddingService:
    """返回 embedding 服务的全局单例。"""
    global _embedding_service
    if _embedding_service is None:
        _embedding_service = EmbeddingService()
    return _embedding_service


def get_embeddings() -> HuggingFaceEmbeddings:
    """兼容旧接口。"""

    return get_embedding_service().get_embeddings()


async def preload_embeddings() -> HuggingFaceEmbeddings:
    """启动期可选预热。"""

    return await get_embedding_service().aget_embeddings()
