# 集中管理这个项目的所有配置、避免硬编码
from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache

class Settings(BaseSettings):  # 强制要求写类型注解

    # 都是设置从哪里读取，怎么读取的问题
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra='ignore'
    )

    # 应用配置
    APP_NAME: str = "今日头条"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    #mysql数据库配置
    MYSQL_HOST: str = "127.0.0.1"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = ""
    MYSQL_DB_NAME: str = "news_app"
    MYSQL_DB_POOL_SIZE: int = 20
    MYSQL_DB_OVERFLOW: int = 40

    # Redis配置
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_MAX_CONNECTIONS: int = 50

    # RabbitMQ配置
    RABBITMQ_HOST: str = "127.0.0.1"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_VHOST: str = "/"


    # 限流配置
    RATE_LIMIT_PER_SECOND: int = 3
    RATE_LIMIT_PER_MINUTE: int = 100
    TOKEN_BUCKET_CAPACITY: int = 10  # 令牌桶容量（支持突发流量)
    TOKEN_RATE: float = 5.0  # 令牌生成速率（个/秒）
    RATE_LIMIT_DIMENSION: str = "combined"  # 限流维度：ip/user_id/combined
    # ====================== 接口防刷配置 ======================
    IP_RATE_LIMIT: int = 60  # IP访问频率限制（次/分钟）
    USER_RATE_LIMIT: int = 100  # 用户访问频率限制（次/分钟）
    MALICIOUS_THRESHOLD: int = 10  # 恶意请求阈值（次/秒）
    BLACKLIST_DURATION: int = 3600  # 黑名单封禁时间（秒）
    SLIDING_WINDOW_SIZE: int = 60  # 滑动窗口大小（秒）
    ENABLE_LOCAL_FALLBACK: bool = True # 是否启用本地限流降级
    RETRY_AFTER: int = 1  # 限流触发后的重试时间（秒）
    ENABLE_RATE_LIMIT_LOGGING: bool = True  # 是否记录限流日志


# 把类中的方法“伪装” 成属性（变量）来访问，不用加括号 () 调用；
# 同时能实现对属性的可控访问（读取、修改、删除），避免直接操作类的内部变量带来的问题。
    @property
    def MYSQL_DATABASE_URL(self) ->str:
        return f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB_NAME}?charset=utf8mb4"

@lru_cache # Least Recently Used Cache，最近最少使用缓存
def get_settings() ->Settings:
    return Settings()


