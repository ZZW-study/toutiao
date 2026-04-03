# -*- coding: utf-8 -*-
"""
新闻爬虫数据存储 CRUD
优化版本：解决N+1查询问题，使用批量操作提升性能
"""
import hashlib
from datetime import datetime, timezone
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession

from models.news import News, Category
from services.news_spider import NewsItem
from utils.logger import get_logger

logger = get_logger(name="NewsSpiderCRUD")


class NewsSpiderCRUD:

    @staticmethod
    def generate_news_hash(title: str, content: str) -> str:
        """生成新闻唯一标识哈希，用于去重"""
        content_hash = hashlib.md5(f"{title}{content[:200]}".encode()).hexdigest()
        return content_hash

    @staticmethod
    async def check_news_exists(db: AsyncSession, title: str, content: str) -> bool:
        """检查新闻是否已存在"""
        stmt = select(func.count(News.id)).where(News.title == title)
        result = await db.execute(stmt)
        count = result.scalar_one()
        return count > 0

    @staticmethod
    async def _get_existing_titles(db: AsyncSession, titles: list[str]) -> set[str]:
        """
        批量查询已存在的新闻标题
        :param db: 数据库会话
        :param titles: 标题列表
        :return: 已存在的标题集合
        """
        if not titles:
            return set()
        stmt = select(News.title).where(News.title.in_(titles))
        result = await db.execute(stmt)
        return {row[0] for row in result.fetchall()}

    @staticmethod
    async def save_news_item(db: AsyncSession, news_item: NewsItem) -> bool:
        """保存单条新闻"""
        try:
            if await NewsSpiderCRUD.check_news_exists(db, news_item.title, news_item.content):
                logger.debug(f"新闻已存在，跳过: {news_item.title}")
                return False

            news = News(
                title=news_item.title,
                description=news_item.description,
                content=news_item.content,
                image=news_item.image,
                author=news_item.author,
                category_id=news_item.category_id,
                views=0,
                publish_time=news_item.publish_time,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc)
            )
            db.add(news)
            await db.commit()
            logger.info(f"新闻保存成功: {news_item.title}")
            return True
        except Exception as e:
            await db.rollback()
            logger.error(f"保存新闻失败: {news_item.title}, 错误: {str(e)}")
            return False

    @staticmethod
    async def save_news_batch(db: AsyncSession, news_list: list[NewsItem]) -> dict:
        """
        批量保存新闻（优化版本）
        - 批量查询已存在标题，避免N+1查询
        - 批量插入，单次提交
        """
        if not news_list:
            return {"total": 0, "saved": 0, "skipped": 0, "failed": 0}

        saved_count = 0
        skipped_count = 0
        failed_count = 0

        # 第一步：批量查询已存在的标题
        all_titles = [item.title for item in news_list]
        existing_titles = await NewsSpiderCRUD._get_existing_titles(db, all_titles)

        # 第二步：过滤出需要保存的新闻
        news_to_save = []
        for news_item in news_list:
            if news_item.title in existing_titles:
                skipped_count += 1
                logger.debug(f"新闻已存在，跳过: {news_item.title}")
                continue
            news_to_save.append(news_item)

        # 第三步：批量创建新闻对象
        now = datetime.now(timezone.utc)
        news_objects = []
        for news_item in news_to_save:
            news = News(
                title=news_item.title,
                description=news_item.description,
                content=news_item.content,
                image=news_item.image,
                author=news_item.author,
                category_id=news_item.category_id,
                views=0,
                publish_time=news_item.publish_time,
                created_at=now,
                updated_at=now
            )
            news_objects.append(news)

        # 第四步：批量插入并单次提交
        if news_objects:
            try:
                db.add_all(news_objects)
                await db.commit()
                saved_count = len(news_objects)
                logger.info(f"批量保存成功: {saved_count} 条新闻")
            except Exception as e:
                await db.rollback()
                failed_count = len(news_objects)
                logger.error(f"批量保存失败: {str(e)}")

        result = {
            "total": len(news_list),
            "saved": saved_count,
            "skipped": skipped_count,
            "failed": failed_count
        }
        logger.info(f"批量保存完成: {result}")
        return result

    @staticmethod
    async def ensure_categories(db: AsyncSession) -> dict:
        """确保分类表有默认数据"""
        default_categories = [
            {"name": "头条", "sort_order": 1},
            {"name": "社会", "sort_order": 2},
            {"name": "国内", "sort_order": 3},
            {"name": "国际", "sort_order": 4},
            {"name": "娱乐", "sort_order": 5},
            {"name": "体育", "sort_order": 6},
            {"name": "科技", "sort_order": 7},
            {"name": "财经", "sort_order": 8}
        ]

        # 批量查询已存在的分类
        existing_names = set()
        stmt = select(Category.name)
        result = await db.execute(stmt)
        existing_names = {row[0] for row in result.fetchall()}

        # 批量创建缺失的分类
        categories_to_create = []
        for cat_data in default_categories:
            if cat_data["name"] not in existing_names:
                category = Category(
                    name=cat_data["name"],
                    sort_order=cat_data["sort_order"],
                    created_at=datetime.now(timezone.utc),
                    updated_at=datetime.now(timezone.utc)
                )
                categories_to_create.append(category)

        if categories_to_create:
            db.add_all(categories_to_create)
            await db.commit()
            logger.info(f"批量创建分类: {len(categories_to_create)} 个")

        return {"created": len(categories_to_create)}
