# -*- coding: utf-8 -*-
"""缓存模块统一导出。"""

from cache.constants import EMPTY_CACHE_FLAG  # 从 cache.constants 模块导入当前文件后续要用到的对象
from cache.local_cache import LocalLRUCache, local_cache  # 从 cache.local_cache 模块导入当前文件后续要用到的对象
from cache.multi_level_cache import MutiLevelCache, MultiLevelCache, multi_cache, multi_level_cache  # 从 cache.multi_level_cache 模块导入当前文件后续要用到的对象
from cache.redis_cache import CacheUtil, cache, generate_cache_key, logic_cache  # 从 cache.redis_cache 模块导入当前文件后续要用到的对象

__all__ = [  # 把右边计算出来的结果保存到 __all__ 变量中，方便后面的代码继续复用
    "EMPTY_CACHE_FLAG",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    "LocalLRUCache",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    "local_cache",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    "CacheUtil",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    "cache",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    "logic_cache",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    "generate_cache_key",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    "MultiLevelCache",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    "MutiLevelCache",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    "multi_level_cache",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
    "multi_cache",  # 继续执行这一行具体逻辑，推动当前函数或代码块往下运行
]  # 这里把上一段参数、数据结构或函数调用的书写收尾，准备回到外层层级

