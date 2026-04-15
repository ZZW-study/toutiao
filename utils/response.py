"""统一成功响应结构。

虽然 FastAPI 可以直接返回字典，但项目里统一包一层有几个好处：
1. 前端拿到的字段结构始终固定。
2. 后续如果要统一加 `request_id`、分页信息等字段，会更容易扩展。
3. 各个路由不需要反复手写同样的响应格式。
"""

from __future__ import annotations

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


def success_response(message: str = "success", data=None):
    """返回统一的成功响应。

    `jsonable_encoder` 会把 `datetime`、Pydantic 模型等非原生 JSON 类型，
    先转换成字典、字符串等可序列化数据，避免 `JSONResponse` 直接报错。
    """

    content = {
        "code": 200,
        "message": message,
        "data": data,
    }
    return JSONResponse(content=jsonable_encoder(content))
