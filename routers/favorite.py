# -*- coding: utf-8 -*-
"""收藏相关路由。

提供收藏的增删查接口。
"""

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from configs.db import get_db
from crud import favorite
from middlewares.token_bucket_rate_limit import rate_limit_dependency
from models.users import User
from schemas.favorite import FavoriteAddRequest, FavoriteCheckResponse, FavoriteListResponse
from utils.auth import get_current_user
from utils.response import success_response

router = APIRouter(
    prefix="/api/favorite",
    tags=["favorite"],
    dependencies=[Depends(rate_limit_dependency)],
)


@router.get("/check")
async def check_favorite(
    news_id: int = Query(..., alias="newsId"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """检查当前用户是否收藏指定新闻。"""
    is_favorite = await favorite.is_news_favorite(db, user.id, news_id)
    return success_response(
        message="检查收藏状态成功",
        data=FavoriteCheckResponse(isFavorite=is_favorite),
    )


@router.post("/add")
async def add_favorite(
    data: FavoriteAddRequest,
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """添加收藏。"""
    result = await favorite.add_news_favorite(db, user_id=user.id, news_id=data.news_id)
    return success_response(message="添加收藏成功", data=result)


@router.delete("/remove")
async def remove_favorite(
    news_id: int = Query(..., alias="newsId"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """取消收藏。"""
    result = await favorite.remove_news_favorite(db, user_id=user.id, news_id=news_id)
    if not result:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="收藏记录不存在")
    return success_response(message="取消收藏成功")


@router.get("/list")
async def get_favorite_list(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=10, ge=1, le=100, alias="pageSize"),
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """分页获取当前用户收藏列表。"""
    rows, total = await favorite.get_favorite_list(db, user.id, page, page_size)
    favorite_list = [
        {
            **news.__dict__,
            "favorite_time": favorite_time,
            "favorite_id": favorite_id,
        }
        for news, favorite_time, favorite_id in rows
    ]
    has_more = total > page * page_size
    data = FavoriteListResponse(list=favorite_list, total=total, has_more=has_more)
    return success_response(message="获取收藏列表成功", data=data)


@router.delete("/clear")
async def clear_favorite(
    user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """清空当前用户全部收藏。"""
    count = await favorite.remove_all_favorites(db, user.id)
    return success_response(message=f"清空了{count}条记录")
