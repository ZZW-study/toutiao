# -*- coding: utf-8 -*-
"""Redis 资源初始化模块。"""

from __future__ import annotations

from typing import TypeVar
import redis.asyncio as redis
from redis.commands.core import Script

from configs.settings import get_settings

T = TypeVar("T")
settings = get_settings()

class RedisConfig:
    """Redis 运行期配置聚合类。

    把 Redis 相关的配置集中到一个类中，方便统一管理和引用。

    属性说明：
    ----------
    连接参数（从 settings 读取）：
    - HOST: Redis 服务器地址
    - PORT: Redis 服务器端口
    - DB: 数据库编号（0-15）
    - PASSWORD: 认证密码
    - MAX_CONNECTIONS: 连接池最大连接数

    业务调优参数（硬编码的默认值）：
    - TIMEOUT: 命令执行超时时间（秒）
    - HEALTH_CHECK_INTERVAL: 健康检查间隔（秒），定期检测连接是否存活
    - SOCKET_KEEPALIVE: 是否启用 TCP Keep-Alive，防止连接被中间设备断开
    - CACHE_RANDOM_OFFSET: 缓存过期随机偏移（秒），防止缓存雪崩
    - EMPTY_CACHE_EXPIRE: 空缓存标记过期时间（秒），防止缓存穿透
    """

    # 连接参数：从环境变量读取
    HOST = settings.REDIS_HOST
    PORT = settings.REDIS_PORT
    DB = settings.REDIS_DB
    PASSWORD = settings.REDIS_PASSWORD
    MAX_CONNECTIONS = settings.REDIS_MAX_CONNECTIONS or 50

    # 超时与健康检查
    TIMEOUT = 5  
    HEALTH_CHECK_INTERVAL = 30 
    SOCKET_KEEPALIVE = True  

    # 业务调优参数
    CACHE_RANDOM_OFFSET = 300   # 缓存过期时间随机偏移 5 分钟，防止大量 key 同时过期
    EMPTY_CACHE_EXPIRE = 60     # 空值缓存 60 秒，防止缓存穿透


# ==============================================================================
# Redis 连接池
# ==============================================================================
# 连接池的核心作用：
# - 复用连接：避免每次操作都创建新连接，减少 TCP 握手开销
# - 连接限制：max_connections 限制最大连接数，防止连接数失控
# - 健康管理：health_check_interval 定期检测并剔除坏连接
#
# 关键参数说明：
# - decode_responses=True: 自动将 bytes 解码为 str，省去手动 decode
# - socket_timeout: 单次操作超时，防止命令执行卡住
# - socket_connect_timeout: 连接建立超时
# - retry_on_timeout=True: 超时后自动重试
# ==============================================================================

redis_pool = redis.ConnectionPool(
    host=RedisConfig.HOST,
    port=RedisConfig.PORT,
    db=RedisConfig.DB,
    password=RedisConfig.PASSWORD,
    max_connections=RedisConfig.MAX_CONNECTIONS,    # 最大连接数 50
    decode_responses=True,                          # 自动解码 bytes -> str
    socket_timeout=RedisConfig.TIMEOUT,             # 命令超时 5 秒
    socket_connect_timeout=RedisConfig.TIMEOUT,     # 连接超时 5 秒
    socket_keepalive=RedisConfig.SOCKET_KEEPALIVE,  # 启用 TCP Keep-Alive
    health_check_interval=RedisConfig.HEALTH_CHECK_INTERVAL,    # 健康检查间隔 30 秒
    retry_on_timeout=True,                                      # 超时自动重试
)


# 所有需要 Redis 的地方都应该使用这个客户端，而不是创建新连接
redis_client: redis.Redis = redis.Redis(connection_pool=redis_pool)


# ==============================================================================
# 分布式锁安全释放脚本（Lua 脚本）
# ==============================================================================
# 为什么用 Lua 脚本？
# - Redis 执行 Lua 脚本是原子的，不会被其他命令打断
# - 保证"检查锁持有者"和"删除锁"两个操作要么都执行，要么都不执行
#
# 脚本逻辑：
# 1. 获取锁 key 的当前值
# 2. 如果值等于传入的标识（ARGV[1]），说明是当前客户端持有的锁
# 3. 只有持锁者才能删除锁，防止误删其他客户端的锁
# 4. 返回 1 表示删除成功，返回 0 表示锁不属于当前客户端
#
# 使用场景：
# ----------
# # 加锁
# identifier = str(uuid.uuid4())
# await redis_client.set("lock:key", identifier, ex=5, nx=True)
#
# # 解锁（使用脚本）
# await UNLOCK_SCRIPT(keys=["lock:key"], args=[identifier])
# ==============================================================================

UNLOCK_SCRIPT = Script(
    registered_client=redis_client,
    script="""
    -- 分布式锁安全释放脚本
    -- KEYS[1]：分布式锁的 key
    -- ARGV[1]：当前持锁方的唯一标识（如 UUID）

    -- 只有锁的持有者才能释放锁
    if redis.call("get", KEYS[1]) == ARGV[1] then
        -- 锁属于当前客户端，删除锁
        return redis.call("del", KEYS[1])
    else
        -- 锁不属于当前客户端，拒绝删除
        return 0
    end
    """,
)
