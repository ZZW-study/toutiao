# 收藏模块
from pydantic import BaseModel,Field,ConfigDict
from datetime import datetime
from schemas.base import NewsItemBase

# 请求体参数模型类

# 添加收藏的请求体模型类
class FavoriteAddRequest(BaseModel):
    news_id: int = Field(...,alias="newsId")


# 响应体参数模型类

# 用户收藏检查响应模型类
class FavoriteCheckResponse(BaseModel):
    is_favorite: bool = Field(...,alias="isFavorite")


# 规划两个类：一个是新闻模型类 + 收藏的模型类
class FavoriteNewsItemResponse(NewsItemBase):
    favorite_id: int = Field(alias="favoriteId")
    favorite_time: datetime = Field(alias="favoriteTime")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )


# 收藏列表接口响应模型类
class FavoriteListResponse(BaseModel):
    list: list[FavoriteNewsItemResponse] # 给pydantic模型传入字典，会自动校验，成功则创建实例，跟请求体传入的逻辑一样
    total: int
    has_more: bool = Field(alias="hasMore")

    model_config = ConfigDict(
        populate_by_name=True,
        from_attributes=True
    )

