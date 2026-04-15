"""配置与基础资源统一导出。

这个包的设计原则是：
1. `settings` 只负责读取和校验配置。
2. `db`、`redis`、`celery` 分别负责初始化各自的运行时资源。
3. 通过 `__init__` 做少量统一导出，方便常用模块引用。
"""

from configs.settings import Settings, get_settings

__all__ = ["Settings", "get_settings"]
