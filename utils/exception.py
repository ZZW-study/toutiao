# 当你的代码报错时（比如 ZeroDivisionError、KeyError 等），Python 会默认输出一段错误信息（Traceback），
# 告诉你错误发生在哪个文件、哪一行、具体是什么错误。
# traceback 模块让你可以手动控制这些错误信息的获取和展示方式，而不是只用 Python 默认的报错格式。
import traceback
from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from starlette import status

# 开发模式: 返回详细错误信息
# 生产模式: 返回简化错误信息
DEBUG_MODE = True  # 教学项目保持开启


# 出现异常后，都按这样的格式返回给前端

async def http_exception_handler(request: Request, exc: HTTPException):
    # 处理 HTTPException 异常
    # HTTPException 通常是业务逻辑主动抛出的, data 保持 None
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "code": exc.status_code,
            "message": exc.detail,
            "data": None
        }
    )

async def integrity_error_handler(request: Request, exc: IntegrityError):
    # 处理数据库完整性约束的错误
    error_msg = str(exc.orig)
    detail = "数据约束冲突，请检查输入"

    # 判断具体的约束错误类型
    if "username_UNIQUE" in error_msg or "Duplicate entry" in error_msg:
        detail = "用户名已存在"
    elif "FOREIGN KEY" in error_msg:
        detail = "关联数据不存在"

    # 开发模式下返回详细错误信息
    error_data = None
    if DEBUG_MODE:
        error_data = {
            "error_type": "IntegrityError",
            "error_detail": error_msg,
            "stack": traceback.format_exc()
        }

    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "code": 400,
            "message": detail,
            "data": error_data
        }
    )

async def sqlalchemy_error_handler(request: Request, exc: SQLAlchemyError):
    # 处理数据库操作失败
    error_data = None
    if DEBUG_MODE:
        error_data = {
            "error_type": type(exc).__name__,
            "error_detail": str(exc),
            "stack": traceback.format_exc()
        }

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": 500,
            "message": "数据库操作失败，请稍后重试",
            "data": error_data
        }
    )

async def general_exception_handler(request: Request, exc: Exception):
    # 处理所有未捕获的异常
    error_data = None
    if DEBUG_MODE:
        error_data = {
            "error_type": type(exc).__name__,
            "error_detail": str(exc),
            "stack": traceback.format_exc()
        }

    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "code": 500,
            "message": "服务器内部错误，请稍后重试",
            "data": error_data
        }
    )


