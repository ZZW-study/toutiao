from pydantic import BaseModel,Field,ConfigDict
from datetime import datetime
from schemas.base import NewsItemBase

# 第一部分，浏览历史模块的请求体参数模型

# 添加浏览历史记录的请求体类
class ViewHistoryAddRequest(BaseModel):
    news_id: int = Field(...,alias="newsId") 





# 第二部分，浏览历史模块的响应体参数模型

# 返回单个浏览历史记录的响应体类
class ViewHistoryResponse(BaseModel):
    id: int = Field(...)
    user_id: int = Field(...,alias="userId")
    news_id: int = Field(...,alias="newsId")
    view_time: datetime = Field(...,alias="viewTime")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )


# 返回浏览历史记录列表的响应体类
class ViewHistory(NewsItemBase):
    view_time : datetime = Field(...,alias="viewTime")

    model_config = ConfigDict(from_attributes=True,populate_by_name=True)

class ViewHistoryListResponse(BaseModel):
    list: list[ViewHistory]
    total : int = Field(...)
    has_more : bool = Field(...,alias="hasMore")

    model_config = ConfigDict(from_attributes=True,populate_by_name=True)

