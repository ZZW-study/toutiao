# -*- coding: utf-8 -*-
"""浏览历史相关 CRUD。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncResult, AsyncSession

from models.history import ViewHistory
from models.news import News


def _now() -> datetime:
    """返回 naive UTC 时间，避免时区问题。"""
    return datetime.utcnow()


async def add_view_history(news_id: int, user_id: int, db: AsyncSession) -> ViewHistory:
    """新增或刷新浏览历史。

    同一用户对同一新闻只保留一条记录，再次浏览时更新时间。
    """
    stmt = select(ViewHistory).where(
        ViewHistory.user_id == user_id,
        ViewHistory.news_id == news_id,
    )
    result = await db.execute(stmt)
    view_history = result.scalar_one_or_none()

    if view_history is not None:
        # 已存在，更新时间
        now = _now()
        update_stmt = (
            update(ViewHistory)
            .where(ViewHistory.user_id == user_id, ViewHistory.news_id == news_id)
            .values(view_time=now)
        )
        result = await db.execute(update_stmt)
        await db.commit()

        if result.rowcount > 0:
            view_history.view_time = now
        return view_history

    # 不存在，新建记录
    user_view_history = ViewHistory(user_id=user_id, news_id=news_id)
    db.add(user_view_history)
    await db.commit()
    await db.refresh(user_view_history)
    return user_view_history


async def get_view_history_list(
    db: AsyncSession,
    user_id: int,
    page: int,
    page_size: int,
):
    """分页查询用户浏览历史，返回 (total, rows)。"""
    count_result = await db.execute(
        select(func.count(ViewHistory.news_id)).where(ViewHistory.user_id == user_id)
    )
    total = count_result.scalar_one()

    offset = (page - 1) * page_size
    result = await db.execute(
        select(News, ViewHistory.view_time.label("viewTime"))
        .join(ViewHistory, ViewHistory.news_id == News.id)
        .where(ViewHistory.user_id == user_id)
        .order_by(ViewHistory.view_time.desc())
        .offset(offset)
        .limit(page_size)
    )
    return total, result.all()


async def delete_view_history(db: AsyncSession, history_id: int) -> bool:
    """删除指定历史记录。"""
    stmt = delete(ViewHistory).where(ViewHistory.id == history_id)
    result: AsyncResult = await db.execute(stmt)
    await db.commit()
    return result.rowcount > 0


async def clear_view_history(db: AsyncSession, user_id: int) -> bool:
    """清空用户全部浏览历史。"""
    stmt = delete(ViewHistory).where(ViewHistory.user_id == user_id)
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount > 0
