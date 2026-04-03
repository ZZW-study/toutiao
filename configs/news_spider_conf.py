# -*- coding: utf-8 -*-
"""
新闻爬虫配置文件
"""
from pydantic_settings import BaseSettings
from functools import lru_cache


class NewsSpiderSettings(BaseSettings):
    model_config = {"env_file": ".env", "env_file_encoding": "utf-8", "extra": "ignore"}

    FETCH_INTERVAL_HOURS: int = 6
    NEWS_PER_SOURCE: int = 50
    REQUEST_TIMEOUT: int = 30
    MAX_RETRIES: int = 3

    DEFAULT_CATEGORY_ID: int = 1

    CLASSIFICATION_RULES: dict = {
        "头条": ["头条", "热点", "最新", "突发", "快讯", "今日", "最新消息", "重磅"],
        "社会": ["社会", "民生", "百姓", "民众", "公众", "群众", "市民", "村民", "居民", "路人", "行人", "群众", "打工", "求职", "招聘", "工资", "房价", "物价"],
        "国内": ["中国", "北京", "上海", "广州", "深圳", "成都", "杭州", "武汉", "西安", "政府", "政策", "中央", "部委", "省委", "市委", "人大代表", "政协", "国家", "各省", "外地"],
        "国际": ["美国", "英国", "法国", "德国", "日本", "韩国", "朝鲜", "俄罗斯", "欧盟", "北约", "联合国", "外交", "海外", "外国", "境外", "巴西", "印度", "澳大利亚", "加拿大", "国际"],
        "娱乐": ["明星", "电影", "电视剧", "综艺", "演唱会", "演员", "导演", "票房", "网红", "偶像", "歌星", "歌手", "选秀", "综艺", "八卦", "绯闻", "出轨", "分手", "结婚", "离婚", "娱乐"],
        "体育": ["足球", "篮球", "奥运", "世界杯", "欧冠", "NBA", "CBA", "乒乓球", "羽毛球", "网球", "游泳", "田径", "跳水", "体操", "举重", "射击", "跆拳道", "武术", "赛车", "F1", "体育"],
        "科技": ["手机", "电脑", "互联网", "AI", "人工智能", "软件", "硬件", "芯片", "5G", "6G", "华为", "苹果", "小米", "三星", "谷歌", "微软", "腾讯", "阿里", "字节", "百度", "京东", "拼多多", "特斯拉", "新能源", "科技"],
        "财经": ["股票", "基金", "货币", "经济", "金融", "投资", "银行", "股市", "上证", "深证", "美股", "港股", "汇率", "黄金", "原油", "期货", "债券", "理财", "保险", "财经", "证券", "投行", "IPO", "上市"]
    }

    NEWS_SOURCES: list = [
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


@lru_cache
def get_news_spider_settings() -> NewsSpiderSettings:
    return NewsSpiderSettings()
