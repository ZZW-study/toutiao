"""Redis 资源初始化模块。

这里拆分自旧的 `redis_conf.py`，目的是把“Redis 配置”和“Redis 客户端”
放在一个专门的资源模块中，而不是混进总配置文件。
"""

from __future__ import annotations

from typing import TypeVar

import redis.asyncio as redis
from redis.commands.core import Script

from configs.settings import get_settings

T = TypeVar("T")
settings = get_settings()


class RedisConfig:
    """Redis 运行期配置聚合。"""

    HOST = settings.REDIS_HOST
    PORT = settings.REDIS_PORT
    DB = settings.REDIS_DB
    PASSWORD = settings.REDIS_PASSWORD
    MAX_CONNECTIONS = settings.REDIS_MAX_CONNECTIONS or 50

    TIMEOUT = 5
    HEALTH_CHECK_INTERVAL = 30
    SOCKET_KEEPALIVE = True

    CACHE_RANDOM_OFFSET = 300
    LOCK_EXPIRE = 5
    MAX_RETRY = 5
    EMPTY_CACHE_EXPIRE = 60
    CIRCUIT_BREAKER = True


redis_pool = redis.ConnectionPool(
    host=RedisConfig.HOST,
    port=RedisConfig.PORT,
    db=RedisConfig.DB,
    password=RedisConfig.PASSWORD,
    max_connections=RedisConfig.MAX_CONNECTIONS,
    decode_responses=True,
    socket_timeout=RedisConfig.TIMEOUT,
    socket_connect_timeout=RedisConfig.TIMEOUT,
    socket_keepalive=RedisConfig.SOCKET_KEEPALIVE,
    health_check_interval=RedisConfig.HEALTH_CHECK_INTERVAL,
    retry_on_timeout=True,
)

redis_client: redis.Redis = redis.Redis(connection_pool=redis_pool)

UNLOCK_SCRIPT = Script(
    registered_client=redis_client,
    script="""
    -- KEYS[1]：分布式锁的 key
    -- ARGV[1]：当前持锁方的唯一标识
    if redis.call("get", KEYS[1]) == ARGV[1] then
        return redis.call("del", KEYS[1])
    else
        return 0
    end
    """,
)
