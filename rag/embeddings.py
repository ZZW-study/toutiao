# -*- coding: utf-8 -*-
"""Embedding 服务。

这里不再在模块导入时直接加载模型，而是改成显式的服务类 + 惰性初始化。
这样可以避免：
- 导入路由时首屏卡住。
- 测试环境一 import `main` 就尝试加载大模型。
"""

from __future__ import annotations  # 开启延迟解析类型注解，避免前向引用在导入阶段就被过早求值

from pathlib import Path  # 从 pathlib 模块导入当前文件后续要用到的对象
from threading import Lock  # 从 threading 模块导入当前文件后续要用到的对象
from typing import Optional  # 从 typing 模块导入当前文件后续要用到的对象

from starlette.concurrency import run_in_threadpool  # 从 starlette.concurrency 模块导入当前文件后续要用到的对象

try:  # 开始尝试执行可能出错的逻辑，如果报错就会转到下面的异常分支
    from langchain_huggingface import HuggingFaceEmbeddings  # 从 langchain_huggingface 模块导入当前文件后续要用到的对象
except ImportError:  # pragma: no cover - 兼容旧依赖组合
    from langchain_community.embeddings import HuggingFaceEmbeddings  # 从 langchain_community.embeddings 模块导入当前文件后续要用到的对象

from utils.logger import get_logger  # 从 utils.logger 模块导入当前文件后续要用到的对象

logger = get_logger(name="Embeddings")  # 把右边计算出来的结果保存到 logger 变量中，方便后面的代码继续复用

EMBEDDING_MODEL_NAME = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"  # 把这个常量值保存到 EMBEDDING_MODEL_NAME 中，后面会作为固定配置反复使用
MODEL_CACHE_DIR = Path(__file__).parent.parent / "data" / "embedding_model"  # 把这个常量值保存到 MODEL_CACHE_DIR 中，后面会作为固定配置反复使用
EMBEDDING_DIMENSION = 384  # 把这个常量值保存到 EMBEDDING_DIMENSION 中，后面会作为固定配置反复使用


class EmbeddingService:  # 定义 EmbeddingService 类，用来把这一块相关的状态和行为组织在一起
    """统一管理 embedding 模型的生命周期。"""

    def __init__(self) -> None:  # 定义函数 __init__，把一段可以复用的逻辑单独封装起来
        """初始化 embedding 服务的懒加载状态。"""
        self._instance: Optional[HuggingFaceEmbeddings] = None  # 把右边计算出来的结果保存到 _instance 变量中，方便后面的代码继续复用
        self._lock = Lock()  # 把右边计算出来的结果保存到 _lock 变量中，方便后面的代码继续复用

    def _build_sync(self) -> HuggingFaceEmbeddings:  # 定义函数 _build_sync，把一段可以复用的逻辑单独封装起来
        """同步加载 HuggingFace embedding 模型实例。"""
        Path.mkdir(MODEL_CACHE_DIR, exist_ok=True, parents=True)  # 把右边计算出来的结果保存到 Path.mkdir(MODEL_CACHE_DIR, exist_ok 变量中，方便后面的代码继续复用
        logger.info("开始加载 Embedding 模型", model=EMBEDDING_MODEL_NAME)  # 记录一条日志，方便后续排查程序运行过程和定位问题
        embeddings = HuggingFaceEmbeddings(  # 把右边计算出来的结果保存到 embeddings 变量中，方便后面的代码继续复用
            model_name=EMBEDDING_MODEL_NAME,  # 把右边计算出来的结果保存到 model_name 变量中，方便后面的代码继续复用
            cache_folder=str(MODEL_CACHE_DIR),  # 把右边计算出来的结果保存到 cache_folder 变量中，方便后面的代码继续复用
            model_kwargs={"device": "cpu"},  # 把右边计算出来的结果保存到 model_kwargs 变量中，方便后面的代码继续复用
            encode_kwargs={"normalize_embeddings": True},  # 把右边计算出来的结果保存到 encode_kwargs 变量中，方便后面的代码继续复用
        )  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级
        logger.info("Embedding 模型加载完成")  # 记录一条日志，方便后续排查程序运行过程和定位问题
        return embeddings  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    def get_embeddings(self) -> HuggingFaceEmbeddings:  # 定义函数 get_embeddings，把一段可以复用的逻辑单独封装起来
        """同步获取模型实例。"""

        if self._instance is not None:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            return self._instance  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

        with self._lock:  # 以上下文管理的方式使用资源，离开代码块时会自动释放或关闭
            if self._instance is None:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
                self._instance = self._build_sync()  # 把右边计算出来的结果保存到 _instance 变量中，方便后面的代码继续复用
        return self._instance  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

    async def aget_embeddings(self) -> HuggingFaceEmbeddings:  # 定义异步函数 aget_embeddings，调用它时通常需要配合 await 使用
        """异步获取模型实例。

        重型初始化放到线程池中，避免阻塞 FastAPI 事件循环。
        """

        if self._instance is not None:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
            return self._instance  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束

        await run_in_threadpool(self.get_embeddings)  # 等待这个异步操作完成，再继续执行后面的代码
        return self.get_embeddings()  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束


_embedding_service: Optional[EmbeddingService] = None  # 把右边计算出来的结果保存到 _embedding_service 变量中，方便后面的代码继续复用


def get_embedding_service() -> EmbeddingService:  # 定义函数 get_embedding_service，把一段可以复用的逻辑单独封装起来
    """返回 embedding 服务的全局单例。"""
    global _embedding_service  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    if _embedding_service is None:  # 开始判断当前条件是否成立，再决定后面该走哪个分支
        _embedding_service = EmbeddingService()  # 把右边计算出来的结果保存到 _embedding_service 变量中，方便后面的代码继续复用
    return _embedding_service  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束


def get_embeddings() -> HuggingFaceEmbeddings:  # 定义函数 get_embeddings，把一段可以复用的逻辑单独封装起来
    """兼容旧接口。"""

    return get_embedding_service().get_embeddings()  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束


async def preload_embeddings() -> HuggingFaceEmbeddings:  # 定义异步函数 preload_embeddings，调用它时通常需要配合 await 使用
    """启动期可选预热。"""

    return await get_embedding_service().aget_embeddings()  # 把这一行计算出来的结果返回给调用方，当前函数通常也会在这里结束
