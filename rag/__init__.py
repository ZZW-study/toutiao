# -*- coding: utf-8 -*-
"""RAG 模块统一导出。"""

from rag.embeddings import get_embedding_service
from rag.vectorstore import get_vectorstore_service

__all__ = [
    "get_embedding_service",
    "get_vectorstore_service",
]
