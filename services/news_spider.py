# -*- coding: utf-8 -*-
"""
新闻爬虫服务
从RSS和公开API获取新闻，并进行分类处理
"""
import asyncio
import aiohttp
import feedparser
import re
from datetime import datetime, timezone
from typing import Optional
from bs4 import BeautifulSoup
from dataclasses import dataclass

from configs.settings import get_settings
from utils.logger import get_logger

logger = get_logger(name="NewsSpider")

settings = get_settings()


def _now():
    """获取当前UTC时间"""
    return datetime.now(timezone.utc)


@dataclass
class NewsItem:
    title: str
    content: str
    description: str
    image: Optional[str]
    author: Optional[str]
    source: str
    publish_time: datetime
    url: str
    category_id: int = 7


class NewsSpiderService:

    @staticmethod
    def classify_news(title: str, content: str = "", description: str = "") -> int:
        """
        基于关键词匹配进行新闻分类
        返回 category_id
        """
        text = f"{title} {content} {description}".lower()

        category_scores = {}
        for category, keywords in settings.SPIDER_CLASSIFICATION_RULES.items():
            score = sum(1 for keyword in keywords if keyword.lower() in text)
            if score > 0:
                category_scores[category] = score

        if not category_scores:
            return settings.SPIDER_DEFAULT_CATEGORY_ID

        best_category = max(category_scores, key=category_scores.get)
        category_id_map = {
            "头条": 1,
            "社会": 2,
            "国内": 3,
            "国际": 4,
            "娱乐": 5,
            "体育": 6,
            "科技": 7,
            "财经": 8
        }

        return category_id_map.get(best_category, settings.SPIDER_DEFAULT_CATEGORY_ID)

    @staticmethod
    async def fetch_sina_news(page: int = 1) -> list[NewsItem]:
        """抓取新浪新闻"""
        news_list = []
        url = settings.SPIDER_NEWS_SOURCES[0]["url"].format(num=settings.SPIDER_NEWS_PER_SOURCE, page=page)

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=settings.SPIDER_REQUEST_TIMEOUT) as response:
                    if response.status != 200:
                        logger.warning(f"新浪新闻请求失败: {response.status}")
                        return []

                    data = await response.json()
                    items = data.get("result", {}).get("data", [])

                    for item in items:
                        try:
                            title = item.get("title", "")
                            description = item.get("intro", "")[:500]
                            content = item.get("content", "")
                            image = item.get("img_url") or item.get("simg")
                            author = item.get("author", "新浪新闻")
                            publish_time_str = item.get("ctime", "")
                            news_url = item.get("url", "")

                            if not title:
                                continue

                            publish_time = datetime.fromtimestamp(int(publish_time_str), tz=timezone.utc) if publish_time_str else _now()

                            news_item = NewsItem(
                                title=title.strip(),
                                content=content[:5000] if content else description,
                                description=description,
                                image=image,
                                author=author,
                                source="新浪新闻",
                                publish_time=publish_time,
                                url=news_url,
                                category_id=NewsSpiderService.classify_news(title, content, description)
                            )
                            news_list.append(news_item)
                        except Exception as e:
                            logger.error(f"解析新浪新闻条目失败: {str(e)}")
                            continue

        except asyncio.TimeoutError:
            logger.error(f"新浪新闻请求超时: {url}")
        except Exception as e:
            logger.error(f"抓取新浪新闻失败: {str(e)}")

        logger.info(f"从新浪抓取 {len(news_list)} 条新闻")
        return news_list

    @staticmethod
    async def fetch_qq_news() -> list[NewsItem]:
        """抓取腾讯新闻"""
        news_list = []
        url = settings.SPIDER_NEWS_SOURCES[1]["url"]

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=settings.SPIDER_REQUEST_TIMEOUT) as response:
                    if response.status != 200:
                        logger.warning(f"腾讯新闻请求失败: {response.status}")
                        return []

                    xml_content = await response.text()
                    feed = feedparser.parse(xml_content)

                    for entry in feed.entries:
                        try:
                            title = entry.get("title", "")
                            description = entry.get("summary", "")[:500]
                            link = entry.get("link", "")

                            author = "腾讯新闻"
                            if hasattr(entry, "author"):
                                author = entry.author

                            publish_time = _now()
                            if hasattr(entry, "published_parsed") and entry.published_parsed:
                                from time import mktime
                                publish_time = datetime.fromtimestamp(mktime(entry.published_parsed), tz=timezone.utc)

                            image = None
                            if hasattr(entry, "media_content") and entry.media_content:
                                image = entry.media_content[0].get("url")
                            elif hasattr(entry, "enclosures") and entry.enclosures:
                                image = entry.enclosures[0].get("href")

                            content = description
                            if hasattr(entry, "content"):
                                content = entry.content[0].value

                            soup = BeautifulSoup(description, "html.parser")
                            description = soup.get_text()[:500]

                            news_item = NewsItem(
                                title=title.strip(),
                                content=content[:5000],
                                description=description,
                                image=image,
                                author=author,
                                source="腾讯新闻",
                                publish_time=publish_time,
                                url=link,
                                category_id=NewsSpiderService.classify_news(title, content, description)
                            )
                            news_list.append(news_item)
                        except Exception as e:
                            logger.error(f"解析腾讯新闻条目失败: {str(e)}")
                            continue

        except asyncio.TimeoutError:
            logger.error(f"腾讯新闻请求超时: {url}")
        except Exception as e:
            logger.error(f"抓取腾讯新闻失败: {str(e)}")

        logger.info(f"从腾讯抓取 {len(news_list)} 条新闻")
        return news_list

    @staticmethod
    async def fetch_all_news() -> list[NewsItem]:
        """从所有来源抓取新闻"""
        tasks = []

        if settings.SPIDER_NEWS_SOURCES[0]["enabled"]:
            tasks.append(NewsSpiderService.fetch_sina_news())

        if settings.SPIDER_NEWS_SOURCES[1]["enabled"]:
            tasks.append(NewsSpiderService.fetch_qq_news())

        results = await asyncio.gather(*tasks, return_exceptions=True)

        all_news = []
        for result in results:
            if isinstance(result, list):
                all_news.extend(result)
            elif isinstance(result, Exception):
                logger.error(f"抓取任务异常: {str(result)}")

        return all_news
