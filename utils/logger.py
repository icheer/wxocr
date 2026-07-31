"""
日志系统配置模块
"""
import logging
import sys
from pathlib import Path
from logging.handlers import RotatingFileHandler


def setup_logger(name='wxocr', log_file=None, log_level='INFO', log_format=None):
    """
    设置日志记录器（同时配置 root logger 确保所有模块日志都能输出）

    Args:
        name: 日志记录器名称
        log_file: 日志文件路径（可选）
        log_level: 日志级别
        log_format: 日志格式

    Returns:
        logging.Logger: 配置好的日志记录器
    """
    # 配置 root logger，让所有子 logger 都能继承配置
    root_logger = logging.getLogger()
    root_logger.setLevel(getattr(logging, log_level.upper(), logging.INFO))

    # 避免重复添加处理器
    if root_logger.handlers:
        return logging.getLogger(name)

    # 默认日志格式
    if log_format is None:
        log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'

    formatter = logging.Formatter(log_format)

    # 控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # 文件处理器（如果指定了日志文件）
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)

        # 使用 RotatingFileHandler 自动轮转日志
        file_handler = RotatingFileHandler(
            log_file,
            maxBytes=10 * 1024 * 1024,  # 10MB
            backupCount=5,
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(formatter)
        root_logger.addHandler(file_handler)

    # 返回指定名称的 logger
    return logging.getLogger(name)


def get_logger(name=None):
    """
    获取日志记录器

    Args:
        name: 日志记录器名称，默认使用调用模块的名称

    Returns:
        logging.Logger: 日志记录器
    """
    if name is None:
        # 获取调用者的模块名
        import inspect
        frame = inspect.currentframe().f_back
        module = inspect.getmodule(frame)
        name = module.__name__ if module else 'wxocr'

    return logging.getLogger(name)
