# -*- coding: utf-8 -*-
"""FastAPI 应用入口。

负责组装应用：创建实例、注册中间件和路由、管理资源生命周期。
"""

from __future__ import annotations

from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi.errors import RateLimitExceeded

from cache.redis_cache import CacheUtil
from configs.settings import get_settings
from middlewares.token_bucket_rate_limit import custom_rate_limit_handler
from rag import preload_embeddings, preload_vectorstore
from routers import chat, favorite, history, news, users
from utils.exception_handlers import register_exception_handlers
from utils.logger import get_logger

settings = get_settings()
logger = get_logger(name="Application")


@asynccontextmanager
async def lifespan(_: FastAPI):
    """应用启动与关闭逻辑。"""
    # 启动时预热 RAG 资源（可选）
    if settings.RAG_PRELOAD_ON_STARTUP:
        try:
            await preload_embeddings()
            await preload_vectorstore()
            logger.info("RAG 资源预热完成")
        except Exception as exc:
            logger.warning("RAG 预热失败，服务将继续启动", error=str(exc), exc_info=True)

    try:
        yield
    finally:
        # 关闭时释放 Redis 连接
        await CacheUtil.close()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# CORS 配置：允许本地前端跨域访问
origins = [
    "http://localhost",
    "http://localhost:5173",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册异常处理器
register_exception_handlers(app)
app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)


@app.get("/")
async def root():
    """健康检查接口。"""
    return {"msg": "Hello World"}


# 挂载路由
app.include_router(news.router)
app.include_router(users.router)
app.include_router(favorite.router)
app.include_router(history.router)
app.include_router(chat.router)


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
