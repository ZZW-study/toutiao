"""
Redis 核心配置与缓存工具集
功能：Redis连接管理、基础缓存操作、生产级缓存装饰器、逻辑过期缓存
修复：锁安全、数据类型丢失、缓存雪崩/击穿/穿透、异步任务安全
架构：支撑多级缓存架构，适配本地缓存+Redis缓存协同工作
适用：FastAPI 异步项目、高并发接口、热点数据缓存
"""
from typing import TypeVar
import redis.asyncio as redis
from redis.commands.core import Script
from configs.settings import get_settings

# ====================== 泛型与全局配置 ======================
# 泛型定义,代表任意具体类型（比如 str、int、list 等）
T = TypeVar("T")
settings = get_settings()

# ====================== Redis 核心配置类 ======================
class RedisConfig:
    """Redis 配置中心"""
    # ---------------- 连接配置 ----------------
    HOST = settings.REDIS_HOST
    PORT = settings.REDIS_PORT
    DB = settings.REDIS_DB
    PASSWORD = settings.REDIS_PASSWORD
    # 最大连接数：防止Redis连接耗尽，根据服务器配置调整
    MAX_CONNECTIONS = settings.REDIS_MAX_CONNECTIONS or 50
    # 超时时间：命令执行/连接超时
    TIMEOUT = 5
    # 连接健康检查：防止死连接
    HEALTH_CHECK_INTERVAL = 30
    # TCP保活：防止长连接被防火墙断开
    SOCKET_KEEPALIVE = True

    # ---------------- 缓存策略配置 ----------------
    # 缓存过期随机偏移：防止大量缓存同时失效（缓存雪崩）
    CACHE_RANDOM_OFFSET = 300
    # 分布式锁默认过期时间
    LOCK_EXPIRE = 5
    # 锁获取最大重试次数
    MAX_RETRY = 5
    # 空值缓存时间：防止缓存穿透
    EMPTY_CACHE_EXPIRE = 60
    # 熔断开关：Redis宕机时直接跳过缓存，保护数据库
    CIRCUIT_BREAKER = True

# ====================== Redis 异步连接池（单例模式） ======================
# 作用：全局复用连接，避免频繁创建/销毁连接导致的性能损耗
redis_pool = redis.ConnectionPool(
    host=RedisConfig.HOST,
    port=RedisConfig.PORT,
    db=RedisConfig.DB,
    password=RedisConfig.PASSWORD,
    max_connections=RedisConfig.MAX_CONNECTIONS,
    # 自动解码bytes为字符串，无需手动处理编码
    decode_responses=True,
    socket_timeout=RedisConfig.TIMEOUT,
    socket_connect_timeout=RedisConfig.TIMEOUT,
    socket_keepalive=RedisConfig.SOCKET_KEEPALIVE,
    health_check_interval=RedisConfig.HEALTH_CHECK_INTERVAL,
    # 超时自动重试，兼容网络抖动
    retry_on_timeout=True,
)
# 创建全局Redis异步客户端
redis_client: redis.Redis = redis.Redis(connection_pool=redis_pool)

# ====================== 分布式锁 Lua 原子脚本 ======================
# 核心作用：保证解锁原子性，**绝对避免** 线程A删除线程B的锁
# Redis执行Lua脚本是原子操作，不会被其他命令打断
UNLOCK_SCRIPT = Script(
    registered_client=redis_client,
    script="""
    -- KEYS[1]：分布式锁的key
    -- ARGV[1]：当前线程持有的锁唯一标识
    if redis.call("get", KEYS[1]) == ARGV[1] then
        -- 锁归属当前线程，执行删除
        return redis.call("del", KEYS[1])
    else
        -- 锁不属于当前线程，不操作（防止误删）
        return 0
    end
    """
)



