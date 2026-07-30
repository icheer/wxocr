"""
任务管理器

提供并发控制和限流机制
"""
import threading
from contextlib import contextmanager
from utils.logger import get_logger
from api.error_handlers import RateLimitError

logger = get_logger(__name__)


class TaskManager:
    """任务管理器（单例模式）"""

    _instance = None
    _lock = threading.Lock()

    def __new__(cls, max_concurrent=3):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self, max_concurrent=3):
        """
        初始化任务管理器

        Args:
            max_concurrent: 最大并发任务数
        """
        if self._initialized:
            return

        self.max_concurrent = max_concurrent
        self.current_tasks = 0
        self.total_tasks_processed = 0
        self.task_lock = threading.Lock()

        logger.info(f"任务管理器初始化: 最大并发={max_concurrent}")
        self._initialized = True

    def can_accept_task(self) -> bool:
        """
        检查是否可以接受新任务

        Returns:
            bool: 是否可以接受
        """
        with self.task_lock:
            return self.current_tasks < self.max_concurrent

    def get_status(self) -> dict:
        """
        获取任务管理器状态

        Returns:
            dict: 状态信息
        """
        with self.task_lock:
            return {
                'current_tasks': self.current_tasks,
                'max_concurrent': self.max_concurrent,
                'available_slots': self.max_concurrent - self.current_tasks,
                'total_processed': self.total_tasks_processed
            }

    @contextmanager
    def task_slot(self):
        """
        任务槽位上下文管理器

        使用方式:
            with task_manager.task_slot():
                # 执行任务
                process_file(...)

        Raises:
            RateLimitError: 超出并发限制
        """
        # 获取任务槽位
        with self.task_lock:
            if self.current_tasks >= self.max_concurrent:
                logger.warning(f"任务被拒绝: 当前任务数={self.current_tasks}, 上限={self.max_concurrent}")
                raise RateLimitError(
                    message='服务器正忙，请稍后重试',
                    current_tasks=self.current_tasks,
                    max_concurrent=self.max_concurrent
                )

            self.current_tasks += 1
            logger.debug(f"任务开始: 当前任务数={self.current_tasks}/{self.max_concurrent}")

        try:
            yield
        finally:
            # 释放任务槽位
            with self.task_lock:
                self.current_tasks -= 1
                self.total_tasks_processed += 1
                logger.debug(f"任务结束: 当前任务数={self.current_tasks}/{self.max_concurrent}, "
                           f"累计处理={self.total_tasks_processed}")

    def update_max_concurrent(self, new_max: int):
        """
        动态更新最大并发数

        Args:
            new_max: 新的最大并发数
        """
        with self.task_lock:
            old_max = self.max_concurrent
            self.max_concurrent = new_max
            logger.info(f"最大并发数已更新: {old_max} -> {new_max}")


# 全局任务管理器实例
_global_task_manager = None


def get_task_manager(max_concurrent=None):
    """
    获取全局任务管理器实例

    Args:
        max_concurrent: 最大并发数（仅在首次调用时有效）

    Returns:
        TaskManager: 任务管理器实例
    """
    global _global_task_manager

    if _global_task_manager is None:
        from config.settings import Config
        max_concurrent = max_concurrent or Config.MAX_CONCURRENT_TASKS
        _global_task_manager = TaskManager(max_concurrent=max_concurrent)

    return _global_task_manager
