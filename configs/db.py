# -*- coding: utf-8 -*-
"""数据库资源初始化模块。

本模块负责创建和管理数据库连接资源，是整个应用数据访问层的基础设施。

核心职责：
-----------
1. 创建异步数据库引擎（AsyncEngine）
   - 管理连接池，复用数据库连接，避免频繁创建/销毁连接的开销
   - 配置连接超时、连接回收等参数，保证连接稳定性

2. 创建会话工厂（async_sessionmaker）
   - 每个请求通过工厂获取独立的数据库会话
   - 会话隔离确保不同请求的事务不会互相干扰

3. 提供 FastAPI 依赖注入函数 get_db
   - 自动管理会话生命周期：创建 -> 使用 -> 提交/回滚 -> 关闭
   - 异常时自动回滚，保证数据一致性

设计说明：
----------
为什么不把数据库引擎放在 settings.py 里？
- settings.py 只负责"配置值"的读取和校验，属于静态数据
- 数据库引擎是"运行时资源"，需要管理连接池、处理超时等动态行为
- 职责分离让代码更清晰，也便于测试时 mock

使用示例：
----------
在路由中通过依赖注入使用：

    @router.get("/users/{user_id}")
    async def get_user(user_id: int, db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(User).where(User.id == user_id))
        return result.scalar_one_or_none()
"""

from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from configs.settings import get_settings

settings = get_settings()

# 从配置中获取数据库连接 URL
# 格式：mysql+aiomysql://user:password@host:port/database?charset=utf8mb4
ASYNC_DATABASE_URL = settings.MYSQL_DATABASE_URL

# ==============================================================================
# 异步数据库引擎
# ==============================================================================
# 引擎是 SQLAlchemy 的核心对象，负责：
# - 维护连接池（应用程序与数据库之间的连接集合）
# - 执行 SQL 语句
# - 处理数据库方言差异（MySQL、PostgreSQL 等）
#
# 关键参数说明：
# - pool_size: 连接池保持的连接数量，默认 5，生产环境建议 20-50
# - max_overflow: 允许临时创建的额外连接数，pool_size + max_overflow = 最大连接数
# - pool_timeout: 获取连接的超时时间（秒），超时抛出异常
# - pool_recycle: 连接回收时间（秒），防止 MySQL 8 小时断连问题
# - pool_pre_ping: 每次使用前检测连接是否存活，自动剔除坏连接
# - echo: 是否打印 SQL 语句，调试时开启，生产环境关闭
# ==============================================================================

async_engine = create_async_engine(
    url=ASYNC_DATABASE_URL,
    echo=settings.DEBUG,  # 调试模式下打印 SQL
    pool_size=settings.MYSQL_DB_POOL_SIZE,  # 连接池大小：20
    max_overflow=settings.MYSQL_DB_OVERFLOW,  # 溢出连接数：40，最大连接数 = 20 + 40 = 60
    pool_timeout=30,  # 获取连接超时 30 秒
    pool_recycle=3600,  # 连接回收时间 1 小时，防止 MySQL wait_timeout 断连
    pool_pre_ping=True,  # 使用前检测连接健康状态
    connect_args={
        "charset": "utf8mb4",  # 字符集，支持 emoji 和中文
        "connect_timeout": 10,  # 连接建立超时 10 秒
    },
)

# ==============================================================================
# 会话工厂
# ==============================================================================
# 会话（Session）是数据库操作的入口，提供：
# - 事务管理：begin/commit/rollback
# - 对象缓存：同一事务内多次查询同一对象，返回同一实例
# - 延迟加载：按需查询关联对象
#
# async_sessionmaker 是工厂类，每次调用()生成一个新的会话实例
# expire_on_commit=False: 提交后对象属性仍可访问，避免延迟加载问题
# ==============================================================================

AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,  # 提交后对象不过期，属性仍可访问
)


async def get_db():
    """FastAPI 数据库会话依赖注入函数。

    这个函数是 FastAPI 依赖注入系统的核心，负责：
    1. 为每个请求创建独立的数据库会话
    2. 请求结束后自动提交或回滚事务
    3. 确保会话正确关闭，释放连接回连接池

    工作流程：
    ----------
    1. 请求进入 -> 创建新会话
    2. 业务代码执行数据库操作
    3. 业务代码正常结束 -> 提交事务（commit）
    4. 业务代码抛出异常 -> 回滚事务（rollback）
    5. 无论成功失败 -> 关闭会话（close），连接归还连接池

    使用方式：
    ----------
    @router.get("/items")
    async def get_items(db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(Item))
        return result.scalars().all()

    注意事项：
    ----------
    - 不要在函数外部存储 db 对象，它只在请求生命周期内有效
    - 如果需要手动控制事务，可以使用 db.begin() / db.commit()
    """

    async with AsyncSessionLocal() as session:
        try:
            # 业务代码执行完毕后自动提交
            yield session
            await session.commit()
        except Exception:
            # 发生异常时回滚事务，保证数据一致性
            await session.rollback()
            raise
        finally:
            # 无论成功失败，都关闭会话释放资源
            await session.close()
