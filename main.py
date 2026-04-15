"""FastAPI 应用入口。

这个文件负责把项目真正“组装起来”：
1. 创建 FastAPI 实例。
2. 注册中间件、异常处理器和路由。
3. 在启动和关闭时处理缓存、RAG 预热等资源生命周期。

如果把整个项目类比成一台机器，这里就是总装车间。
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
    """统一管理应用启动与关闭逻辑。

    启动时：
    - 按配置决定是否预热 embedding 和向量库。
    - 即使预热失败，也不阻止 HTTP 服务启动，避免 AI 子系统问题拖垮整个应用。

    关闭时：
    - 主动关闭 Redis 连接池，释放外部资源。
    """

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
        await CacheUtil.close()


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# 这里允许本地前端开发环境跨域访问后端接口。
# 如果以后要上线正式环境，通常会把允许域名收得更严格。
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

# 全局异常处理器要尽早注册，这样后续路由抛出的异常才能统一格式化。
register_exception_handlers(app)
app.add_exception_handler(RateLimitExceeded, custom_rate_limit_handler)


@app.get("/")
async def root():
    """基础健康检查接口。"""

    return {"msg": "Hello World"}


# 路由拆分成独立模块后，这里只负责挂载，不处理具体业务细节。
app.include_router(news.router)
app.include_router(users.router)
app.include_router(favorite.router)
app.include_router(history.router)
app.include_router(chat.router)


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
