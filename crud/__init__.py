# -*- coding: utf-8 -*-
"""CRUD 数据访问层统一导出。

这里不再导出不存在的函数名，而是直接导出各个 CRUD 模块对象。

这样做有两个好处：
1. `from crud import users/news/...` 的写法能稳定工作。
2. 不会因为 `__init__.py` 中误写了一个不存在的方法名，导致整个包导入失败。

项目中的路由层目前主要就是按"导入模块，再调用模块内函数"的方式使用 CRUD，
所以导出模块对象是最稳妥、最贴合现状的做法。
"""

from . import favorite, history, news, news_spider, users

__all__ = [
    "users",
    "news",
    "favorite",
    "history",
    "news_spider",
]
