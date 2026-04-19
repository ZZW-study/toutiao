# -*- coding: utf-8 -*-
"""项目统一配置中心。

本模块是整个应用的配置管理核心，基于 Pydantic Settings 实现类型安全的配置管理。

核心职责：
-----------
1. 集中管理所有配置项
   - 数据库连接参数（MySQL、Redis、RabbitMQ）
   - 业务参数（限流、爬虫、LLM）
   - 环境相关配置（调试模式、API 密钥）

2. 自动读取环境变量
   - 优先从 .env 文件读取
   - 支持默认值，无 .env 也能运行
   - 类型自动转换和校验

3. 提供计算属性
   - 数据库连接 URL（动态拼接）
   - 爬虫分类规则（关键词映射）
   - 新闻源配置（数据源列表）

设计理念：
----------
为什么用 Pydantic Settings？
- 类型安全：配置项有明确类型，启动时就能发现配置错误
- 环境隔离：开发/测试/生产环境通过不同 .env 文件区分
- 文档友好：每个配置项都有注释，新成员容易理解

配置加载顺序：
--------------
1. 类字段默认值
2. .env 文件中的值（覆盖默认值）
3. 环境变量中的值（覆盖 .env）

使用示例：
----------
from configs.settings import get_settings
settings = get_settings()
print(settings.MYSQL_HOST)  # 访问配置项
print(settings.MYSQL_DATABASE_URL)  # 访问计算属性
"""

from __future__ import annotations

from functools import lru_cache

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """项目运行时配置类。

    所有配置项都在这里定义，每个字段对应一个环境变量。
    字段名不区分大小写，所以 MYSQL_HOST 和 mysql_host 都能读取到同一个变量。

    配置分组：
    ----------
    1. 应用基础配置：应用名称、版本、调试模式
    2. MySQL 配置：数据库连接参数
    3. Redis 配置：缓存和分布式锁
    4. RabbitMQ 配置：消息队列
    5. 限流配置：API 访问频率限制
    6. 防刷配置：恶意请求防护
    7. LLM/RAG 配置：大语言模型和向量检索
    8. 爬虫配置：新闻抓取参数
    """

    model_config = SettingsConfigDict(
        env_file=".env",  # 从 .env 文件读取环境变量
        env_file_encoding="utf-8",  # 文件编码
        case_sensitive=False,  # 字段名不区分大小写
        extra="ignore",  # 忽略未定义的环境变量
    )


    APP_NAME: str = "今日头条"  # 应用名称，用于日志和界面显示
    APP_VERSION: str = "1.0.0"  # 应用版本号
    DEBUG: bool = True  # 调试模式：开启后打印 SQL、详细错误信息等



    MYSQL_HOST: str = "127.0.0.1"  # 数据库主机地址
    MYSQL_PORT: int = 3306  # 数据库端口
    MYSQL_USER: str = "root"  # 数据库用户名
    MYSQL_PASSWORD: str = ""  # 数据库密码（生产环境必须设置）
    MYSQL_DB_NAME: str = "news_app"  # 数据库名称
    MYSQL_DB_POOL_SIZE: int = 20  # 连接池大小：保持的活跃连接数
    MYSQL_DB_OVERFLOW: int = 40  # 溢出连接数：临时创建的额外连接数



    REDIS_HOST: str = "127.0.0.1"  # Redis 主机地址
    REDIS_PORT: int = 6379  # Redis 端口
    REDIS_DB: int = 0  # Redis 数据库编号（0-15）
    REDIS_PASSWORD: str = ""  # Redis 密码（生产环境建议设置）
    REDIS_MAX_CONNECTIONS: int = 50  # 连接池最大连接数



    RABBITMQ_HOST: str = "127.0.0.1"  # RabbitMQ 主机地址
    RABBITMQ_PORT: int = 5672  # RabbitMQ 端口
    RABBITMQ_USER: str = "guest"  # RabbitMQ 用户名
    RABBITMQ_PASSWORD: str = "guest"  # RabbitMQ 密码
    RABBITMQ_VHOST: str = "/"  # RabbitMQ 虚拟主机,默认的


    RATE_LIMIT_PER_SECOND: int = 3  # 每秒最大请求数
    RATE_LIMIT_PER_MINUTE: int = 100  # 每分钟最大请求数
    TOKEN_BUCKET_CAPACITY: int = 10  # 令牌桶容量：最大突发流量
    TOKEN_RATE: float = 5.0  # 令牌生成速率：每秒补充的令牌数
    RATE_LIMIT_DIMENSION: str = "combined"  # 限流维度：ip/user/combined



    IP_RATE_LIMIT: int = 60  # 单 IP 每分钟最大请求数
    USER_RATE_LIMIT: int = 100  # 单用户每分钟最大请求数
    MALICIOUS_THRESHOLD: int = 10  # 恶意请求判定阈值
    BLACKLIST_DURATION: int = 3600  # 黑名单持续时间（秒）
    SLIDING_WINDOW_SIZE: int = 60  # 滑动窗口大小（秒）
    ENABLE_LOCAL_FALLBACK: bool = True  # Redis 不可用时是否降级到本地限流
    RETRY_AFTER: int = 1  # 限流响应中的 Retry-After 头（秒）
    ENABLE_RATE_LIMIT_LOGGING: bool = True  # 是否记录限流日志



    RAG_PRELOAD_ON_STARTUP: bool = True                    # 启动时是否预热向量库
    LLM_ANALYZE_MODEL: str = "Pro/MiniMaxAI/MiniMax-M2.5"  # 问题分析模型
    LLM_GENERATE_MODEL: str = "gpt-4o-mini"                # 回答生成模型
    OPENAI_API_KEY: str = ""                               # OpenAI API 密钥
    OPENAI_API_BASE: str = "https://api.openai.com/v1"     # API 基础 URL


    SPIDER_FETCH_INTERVAL_HOURS: int = 6  # 抓取间隔（小时）
    SPIDER_NEWS_PER_SOURCE: int = 50  # 每个数据源每次抓取的新闻数量
    SPIDER_REQUEST_TIMEOUT: int = 30  # 请求超时时间（秒）
    SPIDER_MAX_RETRIES: int = 3  # 最大重试次数
    SPIDER_DEFAULT_CATEGORY_ID: int = 1  # 默认分类 ID

    @property
    def MYSQL_DATABASE_URL(self) -> str:
        """拼接 SQLAlchemy 使用的 MySQL 异步连接串。

        连接串格式：
        mysql+aiomysql://user:password@host:port/database?charset=utf8mb4

        为什么用属性而不是常量？
        - 依赖多项基础配置动态组合
        - 基础字段更新时自动反映，无需手动同步

        Returns:
            str: 完整的数据库连接 URL
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

        这是一个基于关键词的简单分类器，用于把抓取到的新闻映射到业务分类。

        工作原理：
        ----------
        1. 遍历每个分类的关键词列表
        2. 统计新闻标题/内容中命中关键词的数量
        3. 选择命中数最多的分类作为新闻分类

        优缺点：
        --------
        - 优点：简单直观，无需训练模型，易于调试
        - 缺点：精度受关键词质量影响，无法处理歧义

        Returns:
            dict[str, list[str]]: 分类名到关键词列表的映射
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

        定义了爬虫从哪些网站抓取新闻，以及每个源的类型和状态。

        数据源类型：
        ------------
        - json: API 接口，返回 JSON 格式数据
        - rss: RSS 订阅源，返回 XML 格式数据

        为什么放配置而不是数据库？
        --------------------------
        - 当前是教学演示项目，固定配置更简单
        - 生产环境可迁移到数据库，支持动态增删

        Returns:
            list[dict[str, str | bool]]: 数据源配置列表
        """

        return [
            {
                "name": "sina",  # 新浪新闻
                "url": "https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2516&k=&num={num}&page={page}",
                "type": "json",  # JSON API
                "enabled": True,  # 是否启用
            },
            {
                "name": "qq",  # 腾讯新闻
                "url": "https://news.qq.com/rss/newsrss.xml",
                "type": "rss",  # RSS 订阅
                "enabled": True,
            },
        ]

    @field_validator("DEBUG", mode="before")
    @classmethod
    def normalize_debug(cls, value):
        """兼容多种 DEBUG 环境变量写法。

        用户可能会用各种方式表示布尔值：
        - 字符串：true/false、yes/no、on/off、1/0
        - 环境名：debug/dev/development、release/prod/production

        这个校验器把这些写法统一转换成 Python 布尔值。

        Args:
            value: 原始配置值

        Returns:
            bool: 标准化后的布尔值
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

    使用 lru_cache 装饰器实现单例模式：
    - 第一次调用时创建实例并缓存
    - 后续调用直接返回缓存的实例
    - 避免重复解析 .env 文件

    为什么用单例？
    --------------
    - 配置在运行期间不会改变
    - 避免重复 I/O 操作（读取 .env 文件）
    - 保证整个应用使用同一份配置

    Returns:
        Settings: 全局配置实例
    """

    return Settings()
