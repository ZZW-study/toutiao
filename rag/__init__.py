# -*- coding: utf-8 -*-
"""RAG 模块统一导出。"""

from rag.embeddings import get_embedding_service, get_embeddings, preload_embeddings
from rag.vectorstore import (
    add_news_to_vectorstore,
    get_vectorstore,
    get_vectorstore_service,
    get_vectorstore_stats,
    preload_vectorstore,
)

__all__ = [
    "get_embedding_service",
    "get_embeddings",
    "preload_embeddings",
    "get_vectorstore_service",
    "get_vectorstore",
    "get_vectorstore_stats",
    "preload_vectorstore",
    "add_news_to_vectorstore",
]

