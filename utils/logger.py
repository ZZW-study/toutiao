"""项目统一日志配置。

为什么不直接到处 `print()`：
1. `print()` 没有日志级别，很难区分普通信息和错误。
2. `print()` 不会自动切分文件，也不方便按天归档。
3. 日志想带额外字段（比如 request_id）时，结构化日志更好用。

这里基于 Loguru 做一层轻封装，给全项目提供统一的日志出口。
"""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

from configs.settings import get_settings

settings = get_settings()

# 先移除 Loguru 默认处理器，避免重复打印。
logger.remove()

if settings.DEBUG:
    # 开发环境优先把日志打印到控制台，方便边调试边观察。
    logger.add(
        sys.stdout,
        format=(
            "<green>{time:YYYY-MM-DD HH:mm:ss}</green> | "
            "<level>{level: <8}</level> | "
            "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
            "<level>{message}</level>"
        ),
        level="DEBUG",
        colorize=True,
    )

log_path = Path("logs")
log_path.mkdir(exist_ok=True)

# 应用主日志：记录 INFO 及以上级别，用于日常排障。
logger.add(
    log_path / "app_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="INFO",
    rotation="00:00",
    retention="30 days",
    compression="zip",
    encoding="utf-8",
)

# 错误日志单独分流，便于快速定位失败请求和异常堆栈。
logger.add(
    log_path / "errors_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="ERROR",
    rotation="00:00",
    retention="30 days",
    compression="zip",
    encoding="utf-8",
)

# 请求日志专门记录接口维度的信息，适合后续做接口耗时分析。
logger.add(
    log_path / "requests_{time:YYYY-MM-DD}.log",
    format=(
        "{time:YYYY-MM-DD HH:mm:ss} | {extra[request_id]} | "
        "{extra[method]} {extra[path]} | {extra[status_code]} | {extra[duration]}ms"
    ),
    level="INFO",
    filter=lambda record: "request_id" in record["extra"],
    rotation="00:00",
    retention="7 days",
    compression="zip",
    encoding="utf-8",
)


def get_logger(name: str | None = None):
    """返回统一风格的日志对象。

    `logger.bind(name=name)` 的作用可以理解成：
    基于全局 logger 复制出一个带固定标签的小分身。
    这样不同模块打出来的日志，会自动带上模块名，排查问题时更容易定位来源。
    """

    if name:
        return logger.bind(name=name)
    return logger
