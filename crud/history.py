from sqlalchemy.ext.asyncio import AsyncSession,AsyncResult
from sqlalchemy import select,update,func,delete
from datetime import datetime, timezone
from models.history import ViewHistory
from models.news import News


def _now():
    """获取当前UTC时间"""
    return datetime.now(timezone.utc)


async def add_view_history(news_id: int,user_id: int,db: AsyncSession):
        stmt = select(ViewHistory).where(ViewHistory.user_id==user_id,ViewHistory.news_id==news_id)
        result = await db.execute(stmt)
        view_history = result.scalar_one_or_none()

        if view_history:
            now = _now()
            stmt = update(ViewHistory).where(ViewHistory.user_id==user_id,ViewHistory.news_id==news_id).values(view_time=now)
            result = await db.execute(stmt)
            await db.commit()
            if result.rowcount > 0:
                view_history.view_time = now
                return view_history
            return view_history

        user_view_history = ViewHistory(user_id=user_id,news_id=news_id)
        db.add(user_view_history)
        await db.commit()
        await db.refresh(user_view_history)

        return user_view_history


async def get_view_history_list(db: AsyncSession,user_id: int,page: int,page_size: int):
        count_query = select(func.count(ViewHistory.news_id)).where(ViewHistory.user_id==user_id)
        count_result = await db.execute(count_query)
        total = count_result.scalar_one()

        offset = (page-1)*page_size

        query = (
            select(News,ViewHistory.view_time.label("viewTime")). \
            join(ViewHistory,ViewHistory.news_id==News.id).\
            where(ViewHistory.user_id==user_id).\
            order_by(ViewHistory.view_time.desc()).\
            offset(offset).\
            limit(page_size)
        )
        result = await db.execute(query)
        view_history_list = result.all()

        return total,view_history_list


async def delete_view_history(db:AsyncSession,history_id:int):
        stmt = delete(ViewHistory).where(ViewHistory.id == history_id)
        result: AsyncResult = await db.execute(stmt)

        return result.rowcount > 0


async def clear_view_history(db: AsyncSession,user_id: int):
        stmt = delete(ViewHistory).where(ViewHistory.user_id==user_id)
        result = await db.execute(stmt)

        return result.rowcount > 0
