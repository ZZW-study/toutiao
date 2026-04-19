# -*- coding: utf-8 -*-
"""统一成功响应结构。

前端拿到的字段结构始终固定，便于扩展。
"""

from __future__ import annotations

from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse


def success_response(message: str = "success", data=None):
    """返回统一的成功响应。"""
    content = {
        "code": 200,
        "message": message,
        "data": data,
    }
    return JSONResponse(content=jsonable_encoder(content))
