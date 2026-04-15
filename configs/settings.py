"""项目统一配置中心。

这个模块基于 Pydantic Settings 做配置管理，目标是：
1. 把环境变量读取逻辑收口到一个地方，避免满项目硬编码。
2. 让每个配置项都带上清晰类型，启动时就能尽早发现配置错误。
3. 给数据库、Redis、爬虫、RAG、Agent 等模块提供统一入口。

对初学者来说，可以把它理解成“整个项目的总开关面板”。
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """项目运行时配置。

    `BaseSettings` 的特点是：
    - 类字段会自动映射到环境变量。
    - 有默认值时，即使没有 `.env` 也能跑起来。
    - 没有通过校验的配置会在启动阶段直接报错，问题暴露更早。
    """

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # ====================== 应用基础配置 ======================
    APP_NAME: str = "今日头条"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True

    # ====================== MySQL 配置 ======================
    MYSQL_HOST: str = "127.0.0.1"
    MYSQL_PORT: int = 3306
    MYSQL_USER: str = "root"
    MYSQL_PASSWORD: str = ""
    MYSQL_DB_NAME: str = "news_app"
    MYSQL_DB_POOL_SIZE: int = 20
    MYSQL_DB_OVERFLOW: int = 40

    # ====================== Redis 配置 ======================
    REDIS_HOST: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""
    REDIS_MAX_CONNECTIONS: int = 50

    # ====================== RabbitMQ 配置 ======================
    RABBITMQ_HOST: str = "127.0.0.1"
    RABBITMQ_PORT: int = 5672
    RABBITMQ_USER: str = "guest"
    RABBITMQ_PASSWORD: str = "guest"
    RABBITMQ_VHOST: str = "/"

    # ====================== 限流配置 ======================
    RATE_LIMIT_PER_SECOND: int = 3
    RATE_LIMIT_PER_MINUTE: int = 100
    TOKEN_BUCKET_CAPACITY: int = 10
    TOKEN_RATE: float = 5.0
    RATE_LIMIT_DIMENSION: str = "combined"

    # ====================== 防刷配置 ======================
    IP_RATE_LIMIT: int = 60
    USER_RATE_LIMIT: int = 100
    MALICIOUS_THRESHOLD: int = 10
    BLACKLIST_DURATION: int = 3600
    SLIDING_WINDOW_SIZE: int = 60
    ENABLE_LOCAL_FALLBACK: bool = True
    RETRY_AFTER: int = 1
    ENABLE_RATE_LIMIT_LOGGING: bool = True

    # ====================== LLM / RAG 配置 ======================
    RAG_PRELOAD_ON_STARTUP: bool = False
    LLM_ANALYZE_MODEL: str = "Pro/MiniMaxAI/MiniMax-M2.5"
    LLM_GENERATE_MODEL: str = "gpt-4o-mini"
    OPENAI_API_KEY: str = ""
    OPENAI_API_BASE: str = "https://api.openai.com/v1"

    # ====================== 爬虫配置 ======================
    SPIDER_FETCH_INTERVAL_HOURS: int = 6
    SPIDER_NEWS_PER_SOURCE: int = 50
    SPIDER_REQUEST_TIMEOUT: int = 30
    SPIDER_MAX_RETRIES: int = 3
    SPIDER_DEFAULT_CATEGORY_ID: int = 1

    @property
    def MYSQL_DATABASE_URL(self) -> str:
        """拼接 SQLAlchemy 使用的 MySQL 连接串。

        用属性而不是常量字段的原因是：
        - 它依赖多项基础配置动态组合。
        - 只要基础字段更新，这里就能自动反映，不需要手动同步多份值。
        """

        return (
            "mysql+aiomysql://"
            f"{self.MYSQL_USER}:{self.MYSQL_PASSWORD}"
            f"@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB_NAME}"
            "?charset=utf8mb4"
        )

    @property
    def SPIDER_CLASSIFICATION_RULES(self) -> dict[str, list[str]]:
        """返回爬虫新闻分类规则。

        这些关键词用于把抓到的新闻粗略映射到业务分类中。
        它不是机器学习模型，而是规则匹配，所以优点是简单直观，
        缺点是精度受关键词质量影响较大。
        """

        return {
            "头条": ["头条", "热点", "最新", "突发", "快讯", "今日", "最新消息", "重磅"],
            "社会": ["社会", "民生", "百姓", "民众", "公众", "群众", "市民", "村民", "居民", "路人", "行人", "群众", "打工", "求职", "招聘", "工资", "房价", "物价"],
            "国内": ["中国", "北京", "上海", "广州", "深圳", "成都", "杭州", "武汉", "西安", "政府", "政策", "中央", "部委", "省委", "市委", "人大代表", "政协", "国家", "各省", "外地"],
            "国际": ["美国", "英国", "法国", "德国", "日本", "韩国", "朝鲜", "俄罗斯", "欧盟", "北约", "联合国", "外交", "海外", "外国", "境外", "巴西", "印度", "澳大利亚", "加拿大", "国际"],
            "娱乐": ["明星", "电影", "电视剧", "综艺", "演唱会", "演员", "导演", "票房", "网红", "偶像", "歌星", "歌手", "选秀", "综艺", "八卦", "绯闻", "出轨", "分手", "结婚", "离婚", "娱乐"],
            "体育": ["足球", "篮球", "奥运", "世界杯", "欧冠", "NBA", "CBA", "乒乓球", "羽毛球", "网球", "游泳", "田径", "跳水", "体操", "举重", "射击", "跆拳道", "武术", "赛车", "F1", "体育"],
            "科技": ["手机", "电脑", "互联网", "AI", "人工智能", "软件", "硬件", "芯片", "5G", "6G", "华为", "苹果", "小米", "三星", "谷歌", "微软", "腾讯", "阿里", "字节", "百度", "京东", "拼多多", "特斯拉", "新能源", "科技"],
            "财经": ["股票", "基金", "货币", "经济", "金融", "投资", "银行", "股市", "上证", "深证", "美股", "港股", "汇率", "黄金", "原油", "期货", "债券", "理财", "保险", "财经", "证券", "投行", "IPO", "上市"],
        }

    @property
    def SPIDER_NEWS_SOURCES(self) -> list[dict[str, str | bool]]:
        """返回新闻抓取源配置。

        这里没有把数据源写进数据库，而是先放在配置里，
        是因为当前项目主要是教学与演示场景，固定配置更简单直接。
        """

        return [
            {
                "name": "sina",
                "url": "https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2516&k=&num={num}&page={page}",
                "type": "json",
                "enabled": True,
            },
            {
                "name": "qq",
                "url": "https://news.qq.com/rss/newsrss.xml",
                "type": "rss",
                "enabled": True,
            },
        ]

    @field_validator("DEBUG", mode="before")
    @classmethod
    def normalize_debug(cls, value):
        """兼容多种 `DEBUG` 写法。

        用户机器上可能会把 `DEBUG` 写成 `release`、`prod`、`0` 这类值。
        如果不做归一化，Pydantic 会把这些字符串当成非法布尔值，导致程序启动失败。
        """

        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production", "false", "0", "off", "no"}:
                return False
            if normalized in {"debug", "dev", "development", "true", "1", "on", "yes"}:
                return True
        return value


@lru_cache
def get_settings() -> Settings:
    """返回全局唯一的配置实例。

    配置基本属于“启动后只读”的数据，非常适合缓存成单例。
    这样整个项目反复调用 `get_settings()` 时，不会重复解析 `.env` 文件。
    """

    return Settings()
