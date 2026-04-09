import time
from threading import RLock,Thread # Reentrant Lock可重入锁,同一个线程可以多次获取这个锁
from typing import Any,Optional,Dict,Type
from cachetools import LRUCache # 封装各类缓存策略的工具库,LRU缓存策略

from utils.logger import get_logger
from cache.constants import EMPTY_CACHE_FLAG
# 本地缓存是纯内存同步操作，无 IO 等待，用线程比异步更轻量、更稳定、无事件循环冲突
class LocalLRUCache:
    """
    本地LRU缓存封装类
    特性：线程安全、TTL自动过期、LRU淘汰、命中率统计(缓存收益)、后台自动清理、上下文管理
    适配多级缓存架构：仅存储热点数据，低延迟高性能
    """
    def __init__(
            self,
            maxsize: int = 1000,
            ttl: int = 300,
            auto_cleanup_interval: int = 60,
            enable_auto_cleanup: bool = True
    ):
        """
        初始化本地LRU缓存
        :param maxsize: 缓存最大容量，默认1000（热点数据专用，小容量）
        :param ttl: 缓存默认过期时间（秒），默认5分钟
        :param auto_cleanup_interval: 后台自动清理间隔（秒）
        :param enable_auto_cleanup: 是否开启自动清理
        """
        self._cache: LRUCache = LRUCache(maxsize=maxsize)  
        self._expire_times:  Dict[Any,float] = {} # 缓存键过期时间
        self._lock: RLock = RLock() # 线程重入锁（高并发）

        # 缓存配置
        self.maxsize = maxsize
        self.ttl = ttl
        self.auto_cleanup_interval = auto_cleanup_interval
        # 空值缓存唯一标识：避免与业务数据冲突
        self.EMPTY_CACHE_FLAG = EMPTY_CACHE_FLAG

        # 缓存监控统计指标
        self.hit_count = 0
        self.miss_count = 0
        self.total_count = 0

        # 后台清理线程控制
        self._cleanup_thread: Optional[Thread] = None  # 线程实例变量
        self._stop_cleanup = False # 线程停止标志

        # 绑定日志模块
        self.logger = get_logger(name="LocalLRUCache")

        # 启动后台自动清理
        if enable_auto_cleanup and self.ttl > 0:
            self._start_auto_cleanup()


    def _start_auto_cleanup(self) ->None:
        """启动守护线程，后台自动清理过期缓存"""
        def cleanup_task(): # cleanup_task 运行在 独立守护子线程 中，time.sleep 仅阻塞子线程，主线程 / 业务线程完全不受影响
            while not self._stop_cleanup:
                try:
                    self._clean_expired()
                    time.sleep(self.auto_cleanup_interval)
                except Exception as e:
                    self.logger.error(f"缓存自动清理异常：{e}")
        
        self._cleanup_thread = Thread( # 设置一个线程执行某任务
            target=cleanup_task, # 指定线程要执行的任务函数：线程启动后，会自动调用 cleanup_task() 这个函数，专门做缓存清理工作。
            daemon=True,
            name="local-cache-cleanup-thread" # 设置为守护线程：核心作用是主程序退出时，这个线程会自动强制结束，不用等它执行完，避免程序关不掉。
        )

        self._cleanup_thread.start() # 开启线程
        self.logger.info(
            "本地缓存后台自动清理启动",  
            interval=self.auto_cleanup_interval,  # 自定义参数：清理间隔,会自动计入日志
            maxsize=self.maxsize,                # 自定义参数：缓存最大容量
            default_ttl=self.ttl                 # 自定义参数：默认过期时间
        )


    def is_expired(self,key: Any) ->bool:
        """判断缓存键是否过期"""
        with self._lock: # with保证进入临界区前获取锁，退出时自动释放，同一时刻只有一个线程能执行被锁保护的代码
            if key not in self._expire_times:
                return True
            return time.time() > self._expire_times[key]


    def get(self,key: Any) ->Optional[Any]:
        """获取缓存数据"""
        with self._lock:
            self.total_count += 1
            # 未命中 / 已过期
            if key not in self._cache or self.is_expired(key):
                self.miss_count += 1
                # 清理无效键
                if key in self._cache:
                    del self._cache[key]
                    del self._expire_times[key]
                self.logger.debug("缓存未命中/已过期", key=key)
                return None
        
        # 缓存命中
        self.hit_count += 1
        value = self._cache[key]
        self.logger.debug("缓存命中",key=key)
        return value
    

    def set(self,key: Any,value: Any,ttl: Optional[int] = None) ->None:
        """设置缓存"""
        if self.maxsize <= 0:
            self.logger.warning("缓存容量为0，跳过写入", key=key)
            return
        
        # 设置过期时间-->设置缓存到LRU类，设置过期时间到_expire_times字典
        with self._lock:
            expire_ttl = ttl or self.ttl
            expire_time = time.time() + expire_ttl
            if value is None:
                self._cache[key] = self.EMPTY_CACHE_FLAG
                self._expire_times[key] = expire_time
                return 
            self._cache[key] = value
            self._expire_times[key] = expire_time
            self.logger.debug("缓存写入成功", key=key, expire_ttl=expire_ttl)


    def delete(self,key: Any) ->None:
        """手动删除指定缓存键"""
        with self._lock:
            if key in self._cache:
                del self._cache[key]
                del self._expire_times[key]
                self.logger.debug("缓存删除成功", key=key)


    def _clean_expired(self) ->int:
        """主动清理所有过期缓存，返回清理数量"""
        with self._lock:
            # 过期的键
            expired_keys = [k for k in self._cache if self.is_expired(k)]
            for key in expired_keys:
                del self._cache[key]
                del self._expire_times[key]
            
        self.logger.info("过期缓存清理成功",count = len(expired_keys))
        return len(expired_keys)
    

    def touch(self,key: Any,ttl: Optional[int] = None) ->bool:
        """刷新缓存过期时间（延长生命周期）"""
        with self._lock:
            if key not in self._cache or self.is_expired(key):
                return False
        
        new_ttl = ttl or self.ttl
        self._expire_times[key] = time.time() + new_ttl
        self.logger.debug("缓存过期时间刷新", key=key, new_ttl=new_ttl)
        return True


    def get_status(self) ->Dict[str,Any]:
        """获取缓存统计信息（监控/性能优化专用）"""
        with self._lock:
            hit_rate = (self.hit_count / self.total_count * 100) if self.total_count > 0 else 0.0
            status = {
                "max_capacity": self.maxsize,
                "current_size": len(self._cache),
                "hit_count": self.hit_count,
                "miss_count": self.miss_count,
                "total_requests": self.total_count,
                "hit_rate": round(hit_rate, 2),
                "default_ttl": self.ttl
            }
            self.logger.info("缓存统计信息", **status)
            return status

    def clear(self) -> None:
        """清除所有缓存"""
        with self._lock:
            self._cache.clear()
            self._expire_times.clear()


    def stop(self) ->None:
        """停止后台清理线程，释放资源"""
        self._stop_cleanup = True
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5) # 让【主线程】停下来，死等【子线程】运行结束，才能继续往下走。让主线程等待清理子线程最多 5 秒，超时后自动继续执行，避免程序卡死。
        self.logger.info("本地缓存后台清理线程已停止")

    def __enter__(self) ->"LocalLRUCache":
        """支持上下文管理器"""
        return self

    def __exit__(
            self,
            exc_type: Optional[Type[BaseException]],
            exc: Optional[BaseException],
            tb: Optional[Any]
    ) -> None:
        """
        上下文退出：自动释放资源
        """
        if exc_type is not None:
            self.logger.error(
                "缓存上下文发生异常",
                exc_type=str(exc_type),
                error=str(exc),
                exc_info=True
            )
        # 安全释放资源
        self.stop()
        self.clear()

    def __del__(self) ->None:
        """析构函数保障资源释放"""
        try:
            self.stop()
        except Exception as e:
            pass

        
# 全局单例
local_cache = LocalLRUCache(maxsize=1000,ttl = 300)

