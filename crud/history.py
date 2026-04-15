"""浏览历史相关 CRUD。"""

from __future__ import annotations

from datetime import datetime

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncResult, AsyncSession

from models.history import ViewHistory
from models.news import News


def _now() -> datetime:
    """返回 naive UTC 时间。

    `ViewHistory.view_time` 同样映射到普通 `DateTime` 字段。
    为了避免历史记录更新时再次出现 naive/aware datetime 比较和落库不一致问题，
    这里与用户 token 统一使用 naive UTC。
    """

    return datetime.utcnow()


async def add_view_history(news_id: int, user_id: int, db: AsyncSession) -> ViewHistory:
    """新增或刷新一条浏览历史。

    数据库层通过 `(user_id, news_id)` 唯一约束保证同一用户对同一新闻只有一条记录。
    因此这里的正确策略不是重复插入，而是：
    1. 先查是否已存在。
    2. 存在则只更新时间。
    3. 不存在再插入新记录。
    """

    stmt = select(ViewHistory).where(
        ViewHistory.user_id == user_id,
        ViewHistory.news_id == news_id,
    )
    result = await db.execute(stmt)
    view_history = result.scalar_one_or_none()

    if view_history is not None:
        now = _now()
        update_stmt = (
            update(ViewHistory)
            .where(ViewHistory.user_id == user_id, ViewHistory.news_id == news_id)
            .values(view_time=now)
        )
        result = await db.execute(update_stmt)
        await db.commit()

        if result.rowcount > 0:
            # 同步刷新内存对象，保证当前请求返回的就是最新 view_time。
            view_history.view_time = now
        return view_history

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
    """分页查询用户浏览历史。

    返回 `(total, rows)`，其中 `rows` 的每一项都是 `(News, viewTime)` 元组，
    方便路由层直接组装响应结构。
    """

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
