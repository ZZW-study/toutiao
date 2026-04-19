# -*- coding: utf-8 -*-
"""项目统一日志配置。

基于 Loguru 封装，提供统一的日志出口：
- 开发环境：控制台彩色输出
- 生产环境：文件日志，按天切割，自动压缩
"""

from __future__ import annotations

import sys
from pathlib import Path

from loguru import logger

from configs.settings import get_settings

settings = get_settings()

# 移除默认处理器
logger.remove()

if settings.DEBUG:
    # 开发环境：控制台彩色输出
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

# 应用主日志：INFO 及以上
logger.add(
    log_path / "app_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="INFO",
    rotation="00:00",
    retention="30 days",
    compression="zip",
    encoding="utf-8",
)

# 错误日志单独分流
logger.add(
    log_path / "errors_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="ERROR",
    rotation="00:00",
    retention="30 days",
    compression="zip",
    encoding="utf-8",
)

# 请求日志
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
    """返回带模块标签的日志对象。"""
    if name:
        return logger.bind(name=name)
    return logger
