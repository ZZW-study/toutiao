# -*- coding: utf-8 -*-
"""
RAG (检索增强生成) 模块

该模块提供向量检索所需的基础设施：
- embeddings: Embedding 模型，将文本转换为向量
- vectorstore: 向量存储，基于 Chroma 实现
- indexer: 新闻索引构建，将新闻导入向量库

RAG 流程：
1. 使用 Embedding 模型将新闻文本转换为向量
2. 将向量存储到 Chroma 向量数据库
3. 查询时，将用户问题转换为向量
4. 在向量库中检索相似向量，返回相关新闻
"""

from rag.vectorstore import get_vectorstore, get_embeddings
from rag.indexer import index_all_news, index_news_by_id

__all__ = [
    "get_vectorstore",
    "get_embeddings",
    "index_all_news",
    "index_news_by_id"
]
