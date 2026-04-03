# 1. 异常处理器注册函数 (utils/exception_handlers.py)
# ------------------------------
from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from utils.exception import (
    http_exception_handler,
    integrity_error_handler,
    sqlalchemy_error_handler,
    general_exception_handler,
)

def register_exception_handlers(app):
    """
    注册全局异常处理：子类在前，父类在后
    """
    # 业务逻辑异常
    app.add_exception_handler(HTTPException, http_exception_handler)
    # 数据库完整性约束错误
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    # 数据库操作错误
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)
    # 兜底：捕获所有未处理的异常
    app.add_exception_handler(Exception, general_exception_handler)
