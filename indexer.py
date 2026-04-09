# -*- coding: utf-8 -*-
"""
新闻索引构建模块

该模块负责将 MySQL 数据库中的新闻导入到 Chroma 向量数据库。
索引构建是 RAG 系统的前置步骤，只有索引过的新闻才能被检索到。

主要功能：
1. 全量索引：将所有新闻导入向量库
2. 增量索引：只导入新增的新闻
3. 单条索引：根据新闻 ID 导入单条新闻

使用场景：
- 系统初始化时：运行全量索引
- 定时任务：运行增量索引，同步新增新闻
- 实时索引：爬虫抓取新闻后立即调用单条索引
"""

import asyncio
from typing import List

from sqlalchemy import select

from configs.db_conf import AsyncSessionLocal
from models.news import News
from rag.vectorstore import add_news_to_vectorstore, get_vectorstore_stats
from utils.logger import get_logger

# 获取日志记录器
logger = get_logger(name="Indexer")


async def index_all_news(batch_size: int = 100) -> dict:
    """
    全量索引所有新闻

    从 MySQL 数据库读取所有新闻，分批导入到 Chroma 向量库。
    适合系统初始化时使用。

    参数:
        batch_size: 每批处理的新闻数量，默认 100
                   分批处理可以避免内存溢出

    返回:
        索引结果字典，包含：
        - total: 总新闻数量
        - indexed: 成功索引的数量
        - skipped: 跳过的数量（可能已存在）
    """
    logger.info(f"开始全量索引，批次大小: {batch_size}")

    total = 0
    indexed = 0
    skipped = 0

    try:
        async with AsyncSessionLocal() as db:
            # ========== 第一步：统计总数 ==========
            count_stmt = select(News.id)
            result = await db.execute(count_stmt)
            all_ids = result.scalars().all()
            total = len(all_ids)

            logger.info(f"共有 {total} 条新闻需要索引")

            # ========== 第二步：分批处理 ==========
            # 分批读取 DB 并调用向量化函数，降低内存占用
            offset = 0

            while offset < total:
                # 查询一批新闻
                stmt = (
                    select(News)
                    .order_by(News.id)
                    .offset(offset)
                    .limit(batch_size)
                )
                result = await db.execute(stmt)
                news_batch = result.scalars().all()

                if not news_batch:
                    break

                # 转换为字典列表，供向量化模块使用
                news_list = []
                for news in news_batch:
                    news_list.append({
                        "id": news.id,
                        "title": news.title,
                        "content": news.content,
                        "category_id": news.category_id,
                    })

                # 添加到向量存储（同步调用），返回成功添加数量
                # 注意：add_news_to_vectorstore 可能内部依赖文件系统或 embedding 模型，
                # 在生产环境中可能需要额外的错误重试或限流。
                added = add_news_to_vectorstore(news_list)
                indexed += added
                skipped += len(news_list) - added

                logger.info(f"已处理 {offset + len(news_batch)}/{total}")

                offset += batch_size

        # ========== 第三步：返回结果 ==========
        result = {
            "total": total,
            "indexed": indexed,
            "skipped": skipped
        }

        logger.info(f"全量索引完成: {result}")

        return result

    except Exception as e:
        logger.error(f"全量索引失败: {e}")
        return {
            "total": total,
            "indexed": indexed,
            "skipped": skipped,
            "error": str(e)
        }


async def index_news_by_id(news_id: int) -> bool:
    """
    索引单条新闻

    根据新闻 ID 从数据库读取新闻并导入向量库。
    适合实时索引场景，如爬虫抓取新闻后立即调用。

    参数:
        news_id: 新闻 ID

    返回:
        True: 索引成功
        False: 索引失败（新闻不存在或其他错误）
    """
    logger.info(f"开始索引新闻 ID: {news_id}")

    try:
        async with AsyncSessionLocal() as db:
            # 查询新闻
            stmt = select(News).where(News.id == news_id)
            result = await db.execute(stmt)
            news = result.scalar_one_or_none()

            if not news:
                logger.warning(f"新闻不存在: {news_id}")
                return False

            # 转换为字典
            news_dict = {
                "id": news.id,
                "title": news.title,
                "content": news.content,
                "category_id": news.category_id
            }

            # 添加到向量存储
            added = add_news_to_vectorstore([news_dict])

            if added > 0:
                logger.info(f"新闻索引成功: {news_id}")
                return True
            else:
                logger.warning(f"新闻索引失败: {news_id}")
                return False

    except Exception as e:
        logger.error(f"索引新闻失败: {e}")
        return False


async def index_news_by_ids(news_ids: List[int]) -> dict:
    """
    批量索引指定 ID 的新闻

    根据新闻 ID 列表批量导入向量库。

    参数:
        news_ids: 新闻 ID 列表

    返回:
        索引结果字典，包含：
        - total: 总数量
        - indexed: 成功索引数量
        - failed: 失败数量
    """
    logger.info(f"开始批量索引 {len(news_ids)} 条新闻")

    total = len(news_ids)
    indexed = 0
    failed = 0

    try:
        async with AsyncSessionLocal() as db:
            # 查询指定 ID 的新闻
            stmt = select(News).where(News.id.in_(news_ids))
            result = await db.execute(stmt)
            news_list = result.scalars().all()

            # 转换为字典列表
            news_dicts = [
                {
                    "id": news.id,
                    "title": news.title,
                    "content": news.content,
                    "category_id": news.category_id
                }
                for news in news_list
            ]

            # 添加到向量存储
            added = add_news_to_vectorstore(news_dicts)
            indexed = added
            failed = total - indexed

        result = {
            "total": total,
            "indexed": indexed,
            "failed": failed
        }

        logger.info(f"批量索引完成: {result}")

        return result

    except Exception as e:
        logger.error(f"批量索引失败: {e}")
        return {
            "total": total,
            "indexed": indexed,
            "failed": total - indexed,
            "error": str(e)
        }


async def reindex_all():
    """
    重建全部索引

    清空现有向量库，重新导入所有新闻。
    适合向量库损坏或模型更换时使用。

    注意：此操作会删除所有现有向量！
    """
    logger.warning("开始重建索引，将删除所有现有向量！")

    try:
        # 删除现有向量库目录
        import shutil
        import os
        from rag.vectorstore import CHROMA_PERSIST_DIR

        if os.path.exists(CHROMA_PERSIST_DIR):
            shutil.rmtree(CHROMA_PERSIST_DIR)
            logger.info("已删除现有向量库")

        # 重置实例缓存
        from rag import vectorstore
        vectorstore._vectorstore_instance = None

        # 重新索引
        result = await index_all_news()

        logger.info(f"索引重建完成: {result}")
        return result

    except Exception as e:
        logger.error(f"重建索引失败: {e}")
        return {"error": str(e)}


# ========== 命令行入口 ==========
# 用于直接运行此脚本进行索引
if __name__ == "__main__":
    print("=" * 50)
    print("新闻索引构建工具")
    print("=" * 50)

    # 显示当前状态
    stats = get_vectorstore_stats()
    print(f"当前向量数量: {stats['total_vectors']}")
    print(f"存储目录: {stats['persist_directory']}")
    print()

    # 执行全量索引
    print("开始全量索引...")
    result = asyncio.run(index_all_news())
    print(f"索引结果: {result}")

    # 显示索引后状态
    stats = get_vectorstore_stats()
    print(f"索引后向量数量: {stats['total_vectors']}")
