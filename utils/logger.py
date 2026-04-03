# 结构化日志模块，代替print，用logger（实例化类），支持日志轮转、异步写入、结构化输出
from loguru import logger
import sys
from pathlib import Path
from configs.settings import get_settings

# 得到全局配置
settings = get_settings()

# 移除默认loguru输出到控制台的默认日志处理器
logger.remove()

# 如果是开发环境--日志全部输出控制台
if settings.DEBUG:
    logger.add(
        sys.stdout, # 通向控制台的输出通道，print就是通过此输出到控制台
        format="<green>{time:YYYY-MM-DD HH:mm:ss}</green> | <level>{level: <8}" \
        "</level> | <cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan>" \
        " - <level>{message}</level>",
        level="DEBUG",
        colorize=True
    )

# 不是开发环境,设置公共存储路径
log_path = Path("logs")
log_path.mkdir(exist_ok=True)

# 普通日志--记录INFO以上的所有日志
logger.add(
    log_path/"app_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="INFO",
    rotation="00:00", # 每天00：00创建新的日志，防止把日志都写在一个文件里面
    retention="30 days", # 日志保留三十天
    compression="zip", #压缩久日志
    encoding="utf-8"
)

# 单独记录ERROR以上日志
logger.add(
    log_path/"errors_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {level: <8} | {name}:{function}:{line} - {message}",
    level="ERROR",
    rotation="00:00",
    retention="30 days",
    compression="zip",
    encoding="utf-8"
)

# 单独记录请求有关的日志，方便APM分析（Application Performance Monitoring（应用性能监控））
logger.add(
    log_path/"requests_{time:YYYY-MM-DD}.log",
    format="{time:YYYY-MM-DD HH:mm:ss} | {extra[request_id]} | {extra[method]} {extra[path]} "
    "| {extra[status_code]} | {extra[duration]}ms",
    level="INFO",
    filter=lambda record: "request_id" in record["extra"],
    rotation="00:00",
    retention="7 days",
    compression="zip",
    encoding="utf-8"
)

# 获取日志实例对象的函数--可传参
def get_logger(name: str = None):
    if name:
        return logger.bind(name=name) # 生成一个「带专属标签的副本」
    else:
        return logger

