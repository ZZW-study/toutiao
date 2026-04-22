# -*- coding: utf-8 -*-
"""FastAPI 应用入口。

负责组装应用：创建实例、注册中间件和路由、管理资源生命周期。
"""

from __future__ import annotations

from contextlib import asynccontextmanager
import importlib.util
from pathlib import Path
import subprocess
import sys

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from rag import get_embedding_service, get_vectorstore_service
from routers import chat, favorite, history, news, users
from cache.redis_cache import CacheUtil
from configs.settings import get_settings
from utils.exception_handlers import register_exception_handlers
from utils.logger import get_logger

settings = get_settings()
logger = get_logger(name="Application")
PROJECT_ROOT = Path(__file__).resolve().parent
CELERY_BASE_COMMAND = [sys.executable, "-m", "celery"]
DEFAULT_CELERY_WORKER_POOL = (
    "solo"
    if sys.platform.startswith("win") or importlib.util.find_spec("eventlet") is None
    else "eventlet"
)

# Celery 子进程
# 子进程是操作系统级别的独立进程，有独立的内存空间和 PID
# 它们与主进程（FastAPI）并行运行，通过 RabbitMQ 消息队列通信
# 主进程崩溃时，子进程可能继续运行（需要手动清理）
celery_worker_process = None  # 执行任务的 Worker
celery_beat_process = None    # 定时调度的 Beat


@asynccontextmanager
async def lifespan(_: FastAPI):
    """应用生命周期管理器。

    lifespan 是 FastAPI 提供的机制，用于管理应用启动和关闭时的资源：
    - yield 之前的代码：应用启动时执行（初始化资源）
    - yield 之后的代码：应用关闭时执行（清理资源）

    使用 @asynccontextmanager 装饰器，让一个函数同时处理启动和关闭逻辑。
    """
    global celery_worker_process, celery_beat_process

    # ========== 启动阶段 ==========
    # 启动 Celery Worker（作为子进程）
    # Worker 负责从队列消费任务并执行
    # subprocess.Popen 创建新进程，不会阻塞主进程
    celery_worker_process = subprocess.Popen(
        [
            *CELERY_BASE_COMMAND,
            "-A",
            "middlewares.celery",
            "worker",
            "-l",
            "info",
            "-P",
            DEFAULT_CELERY_WORKER_POOL,
        ],
        cwd=str(PROJECT_ROOT),
    )
    logger.info("Celery Worker 已启动")

    # 启动 Celery Beat（作为子进程）
    # Beat 负责定时调度，按 CELERY_BEAT_SCHEDULE 配置触发任务
    # 只调度定时任务，代码调用触发的任务不需要 Beat
    celery_beat_process = subprocess.Popen(
        [
            *CELERY_BASE_COMMAND,
            "-A",
            "middlewares.celery",
            "beat",
            "-l",
            "info",
        ],
        cwd=str(PROJECT_ROOT),
    )
    logger.info("Celery Beat 已启动")

    # 启动时预热 RAG 资源（可选）
    if settings.RAG_PRELOAD_ON_STARTUP:
        try:
            await get_embedding_service()
            await get_vectorstore_service()
            logger.info("RAG 资源预热完成")
        except Exception as exc:
            logger.warning("RAG 预热失败，服务将继续启动", error=str(exc), exc_info=True)

    try:
        # yield 暂停函数执行，将控制权交给 FastAPI
        # 此时应用开始接收请求，直到应用关闭才继续执行 finally 块
        yield
    finally:
        # ========== 关闭阶段 ==========
        # 停止 Celery Beat 子进程
        if celery_beat_process:
            celery_beat_process.terminate()
            logger.info("Celery Beat 已停止")
        # 停止 Celery Worker 子进程
        # terminate() 发送终止信号，让子进程优雅退出
        if celery_worker_process:
            celery_worker_process.terminate()
            logger.info("Celery Worker 已停止")
        # 关闭时释放 Redis 连接
        await CacheUtil.close()


# 创建 FastAPI 应用实例
# lifespan=lifespan 将生命周期管理器绑定到应用
# 应用启动时自动调用 lifespan 的启动逻辑，关闭时调用关闭逻辑
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

# 令牌桶限流中间件：每个请求对客户端IP做Redis限流，超出返回429
from middlewares.token_bucket_middleware import TokenBucketRateLimitMiddleware
app.add_middleware(TokenBucketRateLimitMiddleware)

# 注册异常处理器
register_exception_handlers(app)


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
    # ========== Python 模块执行原理 ==========
    # 当你运行 `python main.py` 时，Python 解释器会：
    #
    # 1. 设置特殊变量 __name__：
    #    - 直接运行文件时：__name__ = "__main__"
    #    - 被其他文件 import 时：__name__ = "main"（模块名）
    #
    # 2. 从上到下执行文件中的所有代码：
    #    - import 语句 → 加载依赖模块
    #    - 变量赋值（如 settings, logger）→ 创建对象
    #    - 函数/类定义 → 注册到命名空间（函数体不执行）
    #    - app = FastAPI(...) → 创建应用实例
    #    - 路由注册 → 将路由函数绑定到 app
    #
    # 3. 到达 if __name__ == "__main__": 时：
    #    - 直接运行：条件为 True，执行块内代码
    #    - 被 import：条件为 False，跳过块内代码
    #
    # ========== uvicorn.run() 工作原理 ==========
    # uvicorn.run("main:app", ...) 做了这些事：
    #
    # 1. 解析 "main:app" 字符串：
    #    - "main" 是模块名，"app" 是该模块中的变量名
    #
    # 2. import main 模块（如果还没导入）：
    #    - 这会执行 main.py 中的所有模块级代码
    #    - 创建 app 对象、注册路由等
    #
    # 3. 获取 main.app 对象（FastAPI 实例）
    #
    # 4. 启动 ASGI 服务器，监听 127.0.0.1:8000
    #
    # 5. 接收 HTTP 请求，调用 app 中注册的路由处理函数
    #
    # ========== 为什么这样设计？ ==========
    # - 直接运行：启动开发服务器（reload=True 支持热重载）
    # - 被 import：只提供 app 对象，不启动服务器
    #   这在生产环境很有用，可以用 gunicorn/uvicorn 命令行启动：
    #   $ uvicorn main:app --host 0.0.0.0 --port 8000
    #   这也方便测试：测试文件可以 import app 并发送测试请求
    #
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
