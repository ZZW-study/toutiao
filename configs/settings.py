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

    # ====================== LLM 配置 ======================
    # 分析节点使用的模型（用于问题分析、关键词提取）
    LLM_ANALYZE_MODEL: str = "Pro/MiniMaxAI/MiniMax-M2.5"
    # 生成节点使用的模型（用于回答生成）
    LLM_GENERATE_MODEL: str = "gpt-4o-mini"
    # OpenAI API Key（从环境变量读取）
    OPENAI_API_KEY: str = ""
    # OpenAI API Base URL（从环境变量读取）
    OPENAI_API_BASE: str = "https://api.openai.com/v1"

    # ====================== 爬虫配置 ======================
    # 爬抓取间隔（小时）
    SPIDER_FETCH_INTERVAL_HOURS: int = 6
    # 每个数据源抓取的新闻数量
    SPIDER_NEWS_PER_SOURCE: int = 50
    # 请求超时时间（秒）
    SPIDER_REQUEST_TIMEOUT: int = 30
    # 最大重试次数
    SPIDER_MAX_RETRIES: int = 3
    # 默认分类ID
    SPIDER_DEFAULT_CATEGORY_ID: int = 1

    # 把类中的方法"伪装" 成属性（变量）来访问，不用加括号 () 调用；
    # 同时能实现对属性的可控访问（读取、修改、删除），避免直接操作类的内部变量带来的问题。
    @property
    def MYSQL_DATABASE_URL(self) -> str:
        return f"mysql+aiomysql://{self.MYSQL_USER}:{self.MYSQL_PASSWORD}@{self.MYSQL_HOST}:{self.MYSQL_PORT}/{self.MYSQL_DB_NAME}?charset=utf8mb4"

    @property
    def SPIDER_CLASSIFICATION_RULES(self) -> dict:
        """爬虫分类规则"""
        return {
            "头条": ["头条", "热点", "最新", "突发", "快讯", "今日", "最新消息", "重磅"],
            "社会": ["社会", "民生", "百姓", "民众", "公众", "群众", "市民", "村民", "居民", "路人", "行人", "群众", "打工", "求职", "招聘", "工资", "房价", "物价"],
            "国内": ["中国", "北京", "上海", "广州", "深圳", "成都", "杭州", "武汉", "西安", "政府", "政策", "中央", "部委", "省委", "市委", "人大代表", "政协", "国家", "各省", "外地"],
            "国际": ["美国", "英国", "法国", "德国", "日本", "韩国", "朝鲜", "俄罗斯", "欧盟", "北约", "联合国", "外交", "海外", "外国", "境外", "巴西", "印度", "澳大利亚", "加拿大", "国际"],
            "娱乐": ["明星", "电影", "电视剧", "综艺", "演唱会", "演员", "导演", "票房", "网红", "偶像", "歌星", "歌手", "选秀", "综艺", "八卦", "绯闻", "出轨", "分手", "结婚", "离婚", "娱乐"],
            "体育": ["足球", "篮球", "奥运", "世界杯", "欧冠", "NBA", "CBA", "乒乓球", "羽毛球", "网球", "游泳", "田径", "跳水", "体操", "举重", "射击", "跆拳道", "武术", "赛车", "F1", "体育"],
            "科技": ["手机", "电脑", "互联网", "AI", "人工智能", "软件", "硬件", "芯片", "5G", "6G", "华为", "苹果", "小米", "三星", "谷歌", "微软", "腾讯", "阿里", "字节", "百度", "京东", "拼多多", "特斯拉", "新能源", "科技"],
            "财经": ["股票", "基金", "货币", "经济", "金融", "投资", "银行", "股市", "上证", "深证", "美股", "港股", "汇率", "黄金", "原油", "期货", "债券", "理财", "保险", "财经", "证券", "投行", "IPO", "上市"]
        }

    @property
    def SPIDER_NEWS_SOURCES(self) -> list:
        """爬虫新闻源配置"""
        return [
            {
                "name": "sina",
                "url": "https://feed.mix.sina.com.cn/api/roll/get?pageid=153&lid=2516&k=&num={num}&page={page}",
                "type": "json",
                "enabled": True
            },
            {
                "name": "qq",
                "url": "https://news.qq.com/rss/newsrss.xml",
                "type": "rss",
                "enabled": True
            }
        ]


@lru_cache # Least Recently Used Cache，最近最少使用缓存
def get_settings() -> Settings:
    return Settings()
