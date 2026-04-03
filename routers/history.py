# 浏览历史模块
from fastapi import APIRouter,HTTPException,status,Depends,Query,Path,Request
from sqlalchemy.ext.asyncio import AsyncSession
from crud import history
from utils.auth import get_current_user
from utils.response import success_response
from models.users import User
from schemas.history import ViewHistoryAddRequest,ViewHistoryResponse,ViewHistoryListResponse
from configs.db_conf import get_db
from middlewares.token_bucket_rate_limit import rate_limit_dependency

router = APIRouter(prefix="/api/history",tags=["history"])


@router.post("/add")
async def add_veiw_history(
    request: Request,
    news_id:ViewHistoryAddRequest,
    user:User = Depends(get_current_user),
    db:AsyncSession = Depends(get_db),
    _: None = Depends(rate_limit_dependency)
):
    user_view_history = await history.add_view_history(db=db,news_id=news_id.news_id,user_id=user.id)
    return success_response(message="添加历史浏览记录成功",data=ViewHistoryResponse.model_validate(user_view_history))


@router.get("/list")
async def get_view_history_list(
    request: Request,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    page: int = Query(1,ge=1,description="页码"),
    page_size: int = Query(10,ge=1,le=100,alias="pageSize"),
    _: None = Depends(rate_limit_dependency)
):
    total,view_history_list = await history.get_view_history_list(db=db,user_id=user.id,page=page,page_size=page_size)
    has_more = total > page*page_size

    view_history_list = [
        {
            **news.__dict__,
            "viewTime":viewTime
        }
        for news,viewTime in view_history_list
    ]

    data = ViewHistoryListResponse(list=view_history_list,total=total,hasMore=has_more)
    return success_response(message="获取浏览历史列表成功",data=data)


@router.delete("/delete/{history_id}")
async def delete_view_history(
        request: Request,
        user: User=Depends(get_current_user),
        db: AsyncSession=Depends(get_db),
        history_id: int=Path(...,ge=1),
        _: None = Depends(rate_limit_dependency)
):
        has_delete = await history.delete_view_history(db=db,history_id=history_id)
        if not has_delete:
             raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="历史记录不存在")

        return success_response(message="删除成功")


@router.delete("/clear")
async def clear_view_history_list(
        request: Request,
        user: User = Depends(get_current_user),
        db: AsyncSession = Depends(get_db),
        _: None = Depends(rate_limit_dependency)
):
    has_clear = await history.clear_view_history(db=db,user_id=user.id)
    if not has_clear:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,detail="浏览历史记录不存在")

    return success_response(message="清空成功")