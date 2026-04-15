"""数据库连接与会话工厂。

这个文件主要解决两件事：
1. 在应用启动阶段创建一份全局复用的异步数据库引擎。
2. 给 FastAPI 提供 `get_db` 依赖，统一管理事务提交、回滚和连接释放。

为什么要集中放在这里：
- 路由层不需要关心数据库是怎么连上的。
- CRUD 层只拿到 `AsyncSession` 就能工作，职责会更清晰。
- 事务提交和异常回滚放在同一个出口，行为更稳定，也更容易排查问题。
"""

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from configs.settings import get_settings

settings = get_settings()

# 这里直接复用配置模块拼好的 DSN，避免在多个地方重复拼接数据库地址。
ASYNC_DATABASE_URL = settings.MYSQL_DATABASE_URL

# 异步引擎负责维护连接池。连接池能减少频繁建连/断连的开销，
# 对 Web 项目来说性能收益很明显。
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

# 会话工厂本身不等于数据库连接。
# 它更像一个“创建会话的模具”，每次请求来了再基于它生成新的会话对象。
AsyncSessionLocal = async_sessionmaker(
    bind=async_engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db():
    """提供请求级数据库会话。

    执行流程：
    1. 先创建一份新的会话对象。
    2. 路由和 CRUD 在 `yield` 之后使用这份会话。
    3. 正常结束时统一提交事务。
    4. 中途报错时回滚事务，避免脏数据写入数据库。
    5. 最后一定关闭会话，把连接还回连接池。

    这种写法的好处是：业务代码只专注查什么、改什么，
    而不用在每个接口里重复写 commit / rollback / close。
    """

    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
