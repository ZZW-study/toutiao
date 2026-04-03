from sqlalchemy.ext.asyncio import async_sessionmaker,AsyncSession,create_async_engine
from configs.settings import get_settings


settings = get_settings()
#数据库的url
ASYNC_DATABASE_URL = settings.MYSQL_DATABASE_URL

#创建异步引擎
async_engine = create_async_engine(
    url=ASYNC_DATABASE_URL,
    echo = settings.DEBUG,
    pool_size = settings.MYSQL_DB_POOL_SIZE, # 核心连接数
    max_overflow = settings.MYSQL_DB_OVERFLOW, # 最大溢出连接数
    pool_timeout = 30,   # 获取连接超时时间（秒）
    pool_recycle = 3600, # 连接回收时间（秒），防止连接被MySQL断开
    pool_pre_ping = True, # 连接前ping，确保连接有效
    connect_args = {
        "charset": "utf8mb4",
        "connect_timeout": 10
    }
)

#创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    bind = async_engine,
    class_= AsyncSession,
    expire_on_commit = False # 事务提交后，会话中加载的数据库模型对象（ORM 实例）是否会被 “过期失效”
)

#依赖项，用于获取数据库会话
async def get_db():
    async with AsyncSessionLocal() as session:
        try: 
            yield session       # yield 表明这段代码所在的函数是一个生成器函数
            await session.commit() #commit是数据库事务（Transaction）的核心操作，它只服务于写操作（INSERT/UPDATE/DELETE）
        except Exception:
            await session.rollback() #事务回滚操作的语句，作用是撤销当前数据库事务中所有未提交（uncommitted）的数据库操作
            raise
        finally:
            await session.close()





