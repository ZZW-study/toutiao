"""全局异常处理函数。

FastAPI 允许我们把不同类型的异常统一转换成固定 JSON 结构。
这样前端就不用一会儿解析 `"detail"`，一会儿解析 `"message"`，
接口返回格式会稳定很多。
"""

from __future__ import annotations

import traceback

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette import status

# 教学项目里默认保留详细错误信息，方便本地排查。
# 真正上线时通常会根据环境变量切换成 False。
DEBUG_MODE = True


async def http_exception_handler(request: Request, exc: HTTPException):
    """处理业务层主动抛出的 HTTP 异常。

    这类异常往往是“预期内失败”，例如：
    - 参数非法
    - 未登录
    - 数据不存在
    所以直接把状态码和提示信息原样返回即可。
    """

    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "message": exc.detail,
            "data": None,
        },
    )


async def integrity_error_handler(request: Request, exc: IntegrityError):
    """处理数据库约束冲突。

    常见场景：
    - 用户名重复
    - 外键引用不存在
    - 唯一约束冲突
    """

    error_msg = str(exc.orig)
    detail = "数据约束冲突，请检查输入"

    if "username_UNIQUE" in error_msg or "Duplicate entry" in error_msg:
        detail = "用户名已存在"
    elif "FOREIGN KEY" in error_msg:
        detail = "关联数据不存在"

    error_data = None
    if DEBUG_MODE:
        error_data = {
            "error_type": "IntegrityError",
            "error_detail": error_msg,
            "stack": traceback.format_exc(),
        }

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "code": 400,
            "message": detail,
            "data": error_data,
        },
    )


async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    """处理数据库执行阶段的通用异常。"""

    error_data = None
    if DEBUG_MODE:
        error_data = {
            "error_type": type(exc).__name__,
            "error_detail": str(exc),
            "stack": traceback.format_exc(),
        }

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": 500,
            "message": "数据库操作失败，请稍后重试",
            "data": error_data,
        },
    )


async def general_exception_handler(request: Request, exc: Exception):
    """处理所有未被更具体处理器捕获的异常。"""

    error_data = None
    if DEBUG_MODE:
        error_data = {
            "error_type": type(exc).__name__,
            "error_detail": str(exc),
            "stack": traceback.format_exc(),
        }

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": 500,
            "message": "服务器内部错误，请稍后重试",
            "data": error_data,
        },
    )
