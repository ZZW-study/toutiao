# -*- coding: utf-8 -*-
"""
Embedding 模型配置

该模块负责加载和管理文本向量化模型（Embedding Model）。
Embedding 模型将文本转换为高维向量，使得语义相似的文本在向量空间中距离较近。

使用 HuggingFace 的多语言模型，支持中文：
- 模型名称: paraphrase-multilingual-MiniLM-L12-v2
- 向量维度: 384
- 支持语言: 50+ 种语言，包括中文

优点：
- 离线运行，无需 API 调用
- 中文效果较好
- 模型体积小（约 400MB）
"""

from typing import Optional
from pathlib import Path
from langchain_community.embeddings import HuggingFaceEmbeddings
from utils.logger import get_logger

# 获取日志记录器
logger = get_logger(name="Embeddings")


# ========== 全局变量 ==========
# 缓存 Embedding 模型实例，避免重复加载
_embeddings_instance: Optional[HuggingFaceEmbeddings] = None
embedding_dimension = 384

# ========== 配置--模型名字 ==========
EMBEDDING_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"


# 模型缓存目录
MODEL_CACHE_DIR = Path(__file__).parent.parent / "data" / "embedding_model"


def get_embeddings() -> HuggingFaceEmbeddings:
    """
    获取 Embedding 模型实例（单例模式）

    该函数返回一个全局共享的 Embedding 模型实例。
    首次调用时会加载模型，后续调用直接返回缓存的实例。

    模型加载可能需要几分钟时间（首次运行需要下载模型文件）。

    返回:
        HuggingFaceEmbeddings 实例，可用于文本向量化
    """
    global _embeddings_instance

    # 如果已经加载过，直接返回缓存的实例
    if _embeddings_instance is not None:
        return _embeddings_instance

    logger.info(f"开始加载 Embedding 模型: {EMBEDDING_MODEL_NAME}")

    try:
        # 确保缓存目录存在
        Path.mkdir(MODEL_CACHE_DIR, exist_ok=True, parents=True)

        # ========== 创建 Embedding 模型 ==========
        # model_kwargs: 模型参数
        # - device: 'cpu' 使用 CPU 运行（如果有 GPU 可以改为 'cuda'）
        # encode_kwargs: 编码参数
        # - normalize_embeddings: True 表示对向量进行归一化，使余弦距离等价于点积
        _embeddings_instance = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL_NAME,
            cache_folder=str(MODEL_CACHE_DIR),  
            model_kwargs={
                "device": "cuda"         
            },
            encode_kwargs={
                "normalize_embeddings": True
            }
        )

        logger.info("Embedding 模型加载完成")

    except Exception as e:
        logger.error(f"加载 Embedding 模型失败: {e}")
        raise

    return _embeddings_instance