# -*- coding: utf-8 -*-
"""
手动运行爬虫脚本
"""
import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from configs.db_conf import AsyncSessionLocal
from services.news_spider import NewsSpiderService
from crud.news_spider import NewsSpiderCRUD
from utils.logger import get_logger

logger = get_logger(name="RunSpider")


async def main():
    """主函数"""
    async with AsyncSessionLocal() as db:
        # 1. 确保分类存在
        print("确保分类存在...")
        await NewsSpiderCRUD.ensure_categories(db)

        # 2. 获取当前新闻数量
        result = await db.execute(text("SELECT COUNT(*) FROM news"))
        before_count = result.scalar_one()
        print(f"爬取前新闻数量: {before_count}")

        # 3. 抓取新闻
        print("开始抓取新闻...")
        news_list = await NewsSpiderService.fetch_all_news()
        print(f"抓取到 {len(news_list)} 条新闻")

        if not news_list:
            print("未抓取到任何新闻")
            return

        # 4. 保存新闻
        print("开始保存新闻...")
        save_result = await NewsSpiderCRUD.save_news_batch(db, news_list)
        print(f"保存结果: {save_result}")

        # 5. 获取保存后新闻数量
        result = await db.execute(text("SELECT COUNT(*) FROM news"))
        after_count = result.scalar_one()
        print(f"爬取后新闻数量: {after_count}")
        print(f"新增新闻: {after_count - before_count} 条")


if __name__ == "__main__":
    asyncio.run(main())
