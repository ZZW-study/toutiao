"""数据库资源初始化模块。

这里不存放数据库“配置值本身”，而是负责：
1. 基于 `settings` 创建异步引擎。
2. 创建会话工厂。
3. 提供 FastAPI 依赖 `get_db`。

这比把所有内容都塞进 `settings.py` 更主流，因为：
- 配置和资源初始化职责不同。
- 数据库引擎属于运行时对象，不属于纯配置。
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from configs.settings import get_settings

settings = get_settings()

ASYNC_DATABASE_URL = settings.MYSQL_DATABASE_URL

async_engine = create_async_engine(
    url=ASYNC_DATABASE_URL,
    echo=settings.DEBUG,
    pool_size=settings.MYSQL_DB_POOL_SIZE,
    max_overflow=settings.MYSQL_DB_OVERFLOW,
    pool_timeout=30,
    pool_recycle=3600,
    pool_pre_ping=True,
    connect_args={
        "charset": "utf8mb4",
        "connect_timeout": 10,
    },
)

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    """提供请求级数据库会话。"""

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
