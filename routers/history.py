"""浏览历史相关路由。

提供接口：
- POST `/add`：添加或更新浏览历史（记录用户最后一次浏览时间）
- GET `/list`：获取用户浏览历史的分页列表
- DELETE `/delete/{history_id}`：删除单条浏览历史
- DELETE `/clear`：清空用户所有浏览历史

路由层负责鉴权（`get_current_user`）、限流依赖注入，以及把 CRUD 返回的结果格式化为统一响应。
"""

from fastapi import APIRouter, HTTPException, status, Depends, Query, Path, Request
from sqlalchemy.ext.asyncio import AsyncSession
from crud import history
from utils.auth import get_current_user
from utils.response import success_response
from models.users import User
from schemas.history import (
    ViewHistoryAddRequest,
    ViewHistoryResponse,
    ViewHistoryListResponse,
)
from configs.db_conf import get_db
from middlewares.token_bucket_rate_limit import rate_limit_dependency


router = APIRouter(prefix="/api/history", tags=["history"])


@router.post("/add")
async def add_veiw_history(
    request: Request,
    news_id:ViewHistoryAddRequest,
    user:User = Depends(get_current_user),
    db:AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_dependency)
):
    """添加或更新当前用户的新闻浏览记录。

    - 请求体：`ViewHistoryAddRequest` 包含 `news_id`。
    - 返回：`ViewHistoryResponse`，包含最新的浏览记录信息。
    """
    user_view_history = await history.add_view_history(db=db, news_id=news_id.news_id, user_id=user.id)
    return success_response(message="添加历史浏览记录成功", data=ViewHistoryResponse.model_validate(user_view_history))


@router.get("/list")
async def get_view_history_list(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    page: int = Query(1,ge=1,description="页码"),
    page_size: int = Query(10,ge=1,le=100,alias="pageSize"),
    _: None = Depends(rate_limit_dependency)
):
    """分页获取用户的浏览历史。

    返回结构中 `list` 为按时间倒序的新闻条目，包含 `viewTime` 字段。
    """
    total, view_history_list = await history.get_view_history_list(db=db, user_id=user.id, page=page, page_size=page_size)
    has_more = total > page * page_size

    view_history_list = [
        {
            **news.__dict__,
            "viewTime": viewTime,
        }
        for news, viewTime in view_history_list
    ]

    data = ViewHistoryListResponse(list=view_history_list, total=total, hasMore=has_more)
    return success_response(message="获取浏览历史列表成功", data=data)


@router.delete("/delete/{history_id}")
async def delete_view_history(
        request: Request,
        user: User=Depends(get_current_user),
        db: AsyncSession=Depends(get_db),
        history_id: int=Path(...,ge=1),
        _: None = Depends(rate_limit_dependency)
):
    """删除单条浏览历史（基于 history_id）。"""
    has_delete = await history.delete_view_history(db=db, history_id=history_id)
    if not has_delete:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="历史记录不存在")

    return success_response(message="删除成功")


@router.delete("/clear")
async def clear_view_history_list(
        request: Request,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        _: None = Depends(rate_limit_dependency)
):
    """清空当前用户的所有浏览历史。"""
    has_clear = await history.clear_view_history(db=db, user_id=user.id)
    if not has_clear:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="浏览历史记录不存在")

    return success_response(message="清空成功")