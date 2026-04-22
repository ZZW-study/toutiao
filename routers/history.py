# -*- coding: utf-8 -*-
"""浏览历史相关路由。

提供浏览历史的增删查接口。
"""

from fastapi import APIRouter, Depends, HTTPException, Path, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from configs.db import get_db
from crud import history
from models.users import User
from schemas.history import (
    ViewHistoryAddRequest,
    ViewHistoryListResponse,
    ViewHistoryResponse,
)
from utils.auth import get_current_user
from utils.response import success_response

router = APIRouter(
    prefix="/api/history",
    tags=["history"],
)


@router.post("/add")
async def add_view_history(
    news_id: ViewHistoryAddRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """新增或刷新浏览历史。"""
    user_view_history = await history.add_view_history(
        db=db,
        news_id=news_id.news_id,
        user_id=user.id,
    )
    return success_response(
        message="添加历史浏览记录成功",
        data=ViewHistoryResponse.model_validate(user_view_history),
    )


@router.get("/list")
async def get_view_history_list(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(10, ge=1, le=100, alias="pageSize"),
):
    """分页获取浏览历史。"""
    total, view_history_rows = await history.get_view_history_list(
        db=db,
        user_id=user.id,
        page=page,
        page_size=page_size,
    )
    has_more = total > page * page_size

    view_history_list = [
        {
            **news.__dict__,
            "historyId": history_id,
            "viewTime": view_time,
        }
        for news, history_id, view_time in view_history_rows
    ]

    data = ViewHistoryListResponse(list=view_history_list, total=total, hasMore=has_more)
    return success_response(message="获取浏览历史列表成功", data=data)


@router.delete("/delete/{history_id}")
async def delete_view_history(
    history_id: int = Path(..., ge=1),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """删除单条浏览历史。"""
    has_delete = await history.delete_view_history(db=db, history_id=history_id)
    if not has_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="历史记录不存在")
    return success_response(message="删除成功")


@router.delete("/clear")
async def clear_view_history_list(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """清空当前用户的全部浏览历史。"""
    has_clear = await history.clear_view_history(db=db, user_id=user.id)
    if not has_clear:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="浏览历史记录不存在")
    return success_response(message="清空成功")
