"""浏览历史相关的 CRUD 操作。

职责：
- 记录用户对新闻的浏览历史（增量更新最近浏览时间）
- 提供按页查询浏览历史并返回对应新闻信息
- 支持删除单条与清空历史操作

设计要点：
- 对已存在的历史记录做时间更新，避免重复插入
- 查询接口返回总数 + 分页结果，供路由层封装分页响应
"""

from sqlalchemy.ext.asyncio import AsyncSession, AsyncResult
from sqlalchemy import select, update, func, delete
from datetime import datetime, timezone
from models.history import ViewHistory
from models.news import News


def _now():
    """获取当前 UTC 时间（带时区）。"""
    return datetime.now(timezone.utc)


async def add_view_history(news_id: int, user_id: int, db: AsyncSession):
    """添加或更新用户的浏览历史。

    行为：
    - 如果用户已存在该新闻的浏览记录，则更新 `view_time` 为当前时间；
    - 否则插入一条新的浏览记录。

    返回：插入或更新后的 `ViewHistory` 实例。
    """
    stmt = select(ViewHistory).where(ViewHistory.user_id == user_id, ViewHistory.news_id == news_id)
    result = await db.execute(stmt)
    view_history = result.scalar_one_or_none()

    if view_history:
        now = _now()
        stmt = (
            update(ViewHistory)
            .where(ViewHistory.user_id == user_id, ViewHistory.news_id == news_id)
            .values(view_time=now)
        )
        result = await db.execute(stmt)
        await db.commit()
        if result.rowcount > 0:
            # 同步更新内存对象的时间，便于立即返回最新值
            view_history.view_time = now
            return view_history
        return view_history

    user_view_history = ViewHistory(user_id=user_id, news_id=news_id)
    db.add(user_view_history)
    await db.commit()
    await db.refresh(user_view_history)

    return user_view_history


async def get_view_history_list(db: AsyncSession, user_id: int, page: int, page_size: int):
    """分页查询用户的浏览历史。

    返回值： (total, list)
    - total: 总历史条数
    - list: 列表项为 `(News, viewTime)` 元组，按 `view_time` 倒序。
    """
    count_query = select(func.count(ViewHistory.news_id)).where(ViewHistory.user_id == user_id)
    count_result = await db.execute(count_query)
    total = count_result.scalar_one()

    offset = (page - 1) * page_size

    query = (
        select(News, ViewHistory.view_time.label("viewTime"))
        .join(ViewHistory, ViewHistory.news_id == News.id)
        .where(ViewHistory.user_id == user_id)
        .order_by(ViewHistory.view_time.desc())
        .offset(offset)
        .limit(page_size)
    )
    result = await db.execute(query)
    view_history_list = result.all()

    return total, view_history_list


async def delete_view_history(db: AsyncSession, history_id: int):
    """删除指定 ID 的浏览历史，返回是否删除成功（True/False）。"""
    stmt = delete(ViewHistory).where(ViewHistory.id == history_id)
    result: AsyncResult = await db.execute(stmt)

    return result.rowcount > 0


async def clear_view_history(db: AsyncSession, user_id: int):
    """清空用户的所有浏览历史，返回是否有记录被删除。"""
    stmt = delete(ViewHistory).where(ViewHistory.user_id == user_id)
    result = await db.execute(stmt)

    return result.rowcount > 0
