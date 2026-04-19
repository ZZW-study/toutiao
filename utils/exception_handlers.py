"""异常处理器注册入口。

把注册逻辑单独抽出来的好处是：
- `main.py` 会更干净，只负责调用。
- 如果以后要新增自定义异常类型，只需要改这里。
"""

from __future__ import annotations

from fastapi import HTTPException
from sqlalchemy.exc import IntegrityError, SQLAlchemyError

from utils.exception import (
    general_exception_handler,
    http_exception_handler,
    integrity_error_handler,
    sqlalchemy_error_handler,
)


def register_exception_handlers(app):
    """把所有全局异常处理器挂到 FastAPI 应用上。

    注册顺序遵循一个原则：
    越具体的异常放越前面，越宽泛的异常放越后面。
    否则父类异常会先匹配，把子类异常提前"吃掉"。
    """

    app.add_exception_handler(HTTPException, http_exception_handler)
    app.add_exception_handler(IntegrityError, integrity_error_handler)
    app.add_exception_handler(SQLAlchemyError, sqlalchemy_error_handler)
    app.add_exception_handler(Exception, general_exception_handler)
