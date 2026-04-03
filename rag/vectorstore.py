# -*- coding: utf-8 -*-
"""
向量存储模块

该模块负责管理和操作 Chroma 向量数据库。
Chroma 是一个轻量级的向量数据库，适合中小规模的 RAG 应用。

功能：
1. 初始化向量数据库（如果不存在则创建）
2. 添加新闻向量（带元数据）
3. 相似度检索（返回最相关的文档）

向量数据库结构：
- 每条记录包含：向量、文本内容、元数据（新闻 ID、标题、类别等）
- 使用余弦相似度进行检索
"""

import os
from typing import Optional, List

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.documents import Document

from rag.embeddings import get_embeddings
from utils.logger import get_logger

# 获取日志记录器
logger = get_logger(name="VectorStore")


# ========== 全局变量 ==========
# 缓存向量存储实例，避免重复初始化
_vectorstore_instance: Optional[Chroma] = None


# ========== 配置 ==========
# 向量数据库持久化目录
CHROMA_PERSIST_DIR = os.getenv(
    "CHROMA_PERSIST_DIR",
    os.path.join(os.path.dirname(__file__), "..", "data", "chroma")
)

# 集合名称（Chroma 中类似"表"的概念）
COLLECTION_NAME = "news_collection"


def get_vectorstore() -> Chroma:
    """
    获取向量存储实例（单例模式）

    该函数返回一个全局共享的 Chroma 向量存储实例。
    首次调用时会初始化向量数据库，后续调用直接返回缓存的实例。

    如果持久化目录不存在，会自动创建新的数据库。
    如果持久化目录已存在，会加载已有的向量数据。

    返回:
        Chroma 向量存储实例
    """
    global _vectorstore_instance

    # 如果已经初始化过，直接返回缓存的实例
    if _vectorstore_instance is not None:
        return _vectorstore_instance

    logger.info(f"初始化向量存储，持久化目录: {CHROMA_PERSIST_DIR}")

    try:
        # 确保持久化目录存在
        os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)

        # 获取 Embedding 模型
        embeddings = get_embeddings()

        # ========== 初始化 Chroma 向量存储 ==========
        # persist_directory: 数据持久化目录
        # embedding_function: 用于将文本转换为向量的函数
        # collection_name: 集合名称
        _vectorstore_instance = Chroma(
            persist_directory=CHROMA_PERSIST_DIR,
            embedding_function=embeddings,
            collection_name=COLLECTION_NAME
        )

        # 检查已有数据量
        count = _vectorstore_instance._collection.count()
        logger.info(f"向量存储初始化完成，已有 {count} 条向量")

    except Exception as e:
        logger.error(f"初始化向量存储失败: {e}")
        raise

    return _vectorstore_instance


def add_news_to_vectorstore(
    news_list: List[dict]
) -> int:
    """
    批量添加新闻到向量存储

    将新闻列表转换为向量并存储到 Chroma。
    每条新闻会被转换为一个 Document 对象，包含：
    - page_content: 用于向量化的文本（标题 + 内容）
    - metadata: 元数据（新闻 ID、标题、类别 ID 等）

    参数:
        news_list: 新闻列表，每条新闻是一个字典，包含以下字段：
            - id: 新闻 ID（必需）
            - title: 新闻标题（必需）
            - content: 新闻内容（必需）
            - category_id: 类别 ID（可选）

    返回:
        成功添加的新闻数量
    """
    if not news_list:
        logger.warning("新闻列表为空，跳过添加")
        return 0

    logger.info(f"开始添加 {len(news_list)} 条新闻到向量存储")

    try:
        vectorstore = get_vectorstore()

        # ========== 构建文档列表 ==========
        texts = []
        metadatas = []

        for news in news_list:
            # 跳过关键字段缺失的新闻
            if not news.get("id") or not news.get("title"):
                logger.warning(f"新闻缺少必要字段，跳过: {news}")
                continue

            # 构建用于向量化的文本
            # 同样权重的标题和内容（内容取前 1000 字符）
            title = news["title"]
            content = news.get("content", "")[:1000]
            text = f"标题：{title}\n内容：{content}"

            texts.append(text)

            # 构建元数据
            metadata = {
                "news_id": news["id"],
                "title": title,
                "category_id": news.get("category_id", 0)
            }
            metadatas.append(metadata)

        # ========== 批量添加到向量存储 ==========
        if texts:
            vectorstore.add_texts(texts=texts, metadatas=metadatas)
            logger.info(f"成功添加 {len(texts)} 条新闻到向量存储")

        return len(texts)

    except Exception as e:
        logger.error(f"添加新闻到向量存储失败: {e}")
        return 0


def search_similar_news(
    query: str,
    top_k: int = 5,
    category_id: Optional[int] = None
) -> List[Document]:
    """
    搜索相似新闻

    根据查询文本，在向量存储中检索语义相似度最高的新闻。

    参数:
        query: 查询文本
        top_k: 返回的最大结果数量
        category_id: 类别过滤条件（可选），只返回该类别的新闻

    返回:
        Document 列表，每个 Document 包含：
        - page_content: 新闻文本
        - metadata: 元数据（news_id、title、category_id）
    """
    logger.debug(f"搜索相似新闻 - 查询: '{query}', top_k: {top_k}")

    try:
        vectorstore = get_vectorstore()

        # 构建过滤条件
        filter_dict = None
        if category_id is not None:
            filter_dict = {"category_id": category_id}

        # 执行相似度检索
        results = vectorstore.similarity_search(
            query=query,
            k=top_k,
            filter=filter_dict
        )

        logger.debug(f"检索到 {len(results)} 条结果")
        return results

    except Exception as e:
        logger.error(f"搜索相似新闻失败: {e}")
        return []


def delete_news_from_vectorstore(news_ids: List[int]) -> int:
    """
    从向量存储中删除新闻

    注意：Chroma 的删除操作是按 ID 删除，但这里的 ID 是文档的内部 ID，
    不是我们存储的 news_id。因此需要先查询再删除。

    参数:
        news_ids: 要删除的新闻 ID 列表

    返回:
        删除的文档数量
    """
    logger.info(f"尝试从向量存储删除 {len(news_ids)} 条新闻")

    try:
        vectorstore = get_vectorstore()
        collection = vectorstore._collection

        deleted_count = 0

        # Chroma 需要根据 metadata 查找并删除
        for news_id in news_ids:
            # 查询该 news_id 对应的文档
            results = collection.get(
                where={"news_id": news_id}
            )

            if results and results["ids"]:
                # 删除找到的文档
                collection.delete(ids=results["ids"])
                deleted_count += len(results["ids"])

        logger.info(f"成功删除 {deleted_count} 条向量")

        return deleted_count

    except Exception as e:
        logger.error(f"删除新闻失败: {e}")
        return 0


def get_vectorstore_stats() -> dict:
    """
    获取向量存储统计信息

    返回:
        统计信息字典，包含：
        - total_vectors: 向量总数
        - persist_directory: 持久化目录路径
    """
    try:
        vectorstore = get_vectorstore()
        count = vectorstore._collection.count()

        return {
            "total_vectors": count,
            "persist_directory": CHROMA_PERSIST_DIR
        }

    except Exception as e:
        logger.error(f"获取统计信息失败: {e}")
        return {
            "total_vectors": 0,
            "persist_directory": CHROMA_PERSIST_DIR
        }
