# -*- coding: utf-8 -*-
"""Redis 资源初始化模块。

本模块负责创建和管理 Redis 连接资源，为缓存、分布式锁、限流等功能提供基础设施。

核心职责：
-----------
1. 定义 Redis 连接配置（主机、端口、密码、连接池大小等）
2. 创建连接池和异步 Redis 客户端
3. 提供分布式锁安全释放脚本（Lua 脚本）

为什么单独拆分这个模块？
-----------------------
- 配置（settings.py）只负责读取环境变量
- 资源模块（本文件）负责创建运行时对象
- 职责分离让代码更清晰，也便于测试和替换实现

Redis 在本项目中的应用场景：
---------------------------
1. 多级缓存：作为二级缓存，存储热点数据（L1 是本地内存缓存）
2. 分布式锁：防止并发场景下的重复操作（如重复抓取新闻）
3. 限流计数：配合令牌桶算法实现 API 限流
4. 会话存储：可选的会话后端

使用示例：
----------
# 直接使用全局客户端
from configs.redis import redis_client
await redis_client.set("key", "value", ex=300)

# 在缓存模块中使用
from configs.redis import redis_client
result = await redis_client.get("cache:user:123")
"""

from __future__ import annotations

from typing import TypeVar

import redis.asyncio as redis
from redis.commands.core import Script

from configs.settings import get_settings

T = TypeVar("T")
settings = get_settings()


# ==============================================================================
# Redis 运行期配置聚合
# ==============================================================================
# 把分散在 settings 中的 Redis 相关配置集中管理
# 包含连接参数和业务调优参数两类
# ==============================================================================

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
    - LOCK_EXPIRE: 分布式锁默认过期时间（秒）
    - MAX_RETRY: 最大重试次数
    - EMPTY_CACHE_FLAG: 空缓存标记过期时间（秒），防止缓存穿透
    - CIRCUIT_BREAKER: 是否启用熔断器
    """

    # 连接参数：从环境变量读取
    HOST = settings.REDIS_HOST
    PORT = settings.REDIS_PORT
    DB = settings.REDIS_DB
    PASSWORD = settings.REDIS_PASSWORD
    MAX_CONNECTIONS = settings.REDIS_MAX_CONNECTIONS or 50

    # 超时与健康检查
    TIMEOUT = 5  # 命令执行超时 5 秒
    HEALTH_CHECK_INTERVAL = 30  # 每 30 秒检查一次连接健康状态
    SOCKET_KEEPALIVE = True  # 启用 TCP Keep-Alive

    # 业务调优参数
    CACHE_RANDOM_OFFSET = 300  # 缓存过期时间随机偏移 5 分钟，防止大量 key 同时过期
    LOCK_EXPIRE = 5  # 分布式锁默认 5 秒后自动释放
    MAX_RETRY = 5  # 操作失败最多重试 5 次
    EMPTY_CACHE_FLAG = 60  # 空值缓存 60 秒，防止缓存穿透
    CIRCUIT_BREAKER = True  # 启用熔断器，连续失败后快速失败


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
    max_connections=RedisConfig.MAX_CONNECTIONS,  # 最大连接数 50
    decode_responses=True,  # 自动解码 bytes -> str
    socket_timeout=RedisConfig.TIMEOUT,  # 命令超时 5 秒
    socket_connect_timeout=RedisConfig.TIMEOUT,  # 连接超时 5 秒
    socket_keepalive=RedisConfig.SOCKET_KEEPALIVE,  # 启用 TCP Keep-Alive
    health_check_interval=RedisConfig.HEALTH_CHECK_INTERVAL,  # 健康检查间隔 30 秒
    retry_on_timeout=True,  # 超时自动重试
)

# 全局异步 Redis 客户端
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
