# -*- coding: utf-8 -*-
"""RAG 模块统一导出。"""

from rag.embeddings import get_embedding_service, get_embeddings, preload_embeddings  # 从 rag.embeddings 模块导入当前文件后续要用到的对象
from rag.vectorstore import (  # 从 rag.vectorstore 模块导入当前文件后续要用到的对象
    add_news_to_vectorstore,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    get_vectorstore,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    get_vectorstore_service,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    get_vectorstore_stats,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    preload_vectorstore,  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
)  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级

__all__ = [  # 把右边计算出来的结果保存到 __all__ 变量中，方便后面的代码继续复用
    "get_embedding_service",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    "get_embeddings",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    "preload_embeddings",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    "get_vectorstore_service",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    "get_vectorstore",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    "get_vectorstore_stats",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    "preload_vectorstore",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    "add_news_to_vectorstore",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
]  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级

