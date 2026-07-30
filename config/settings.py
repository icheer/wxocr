"""
应用配置管理模块
"""
import os
from pathlib import Path

# 项目根目录
BASE_DIR = Path(__file__).resolve().parent.parent


class Config:
    """基础配置类"""

    # ==================== 服务配置 ====================
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))
    DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'

    # ==================== 微信OCR配置 ====================
    WCOCR_BIN_PATH = os.getenv('WCOCR_BIN_PATH', str(BASE_DIR / 'wx' / 'opt' / 'wechat' / 'wxocr'))
    WCOCR_LIB_PATH = os.getenv('WCOCR_LIB_PATH', str(BASE_DIR / 'wx' / 'opt' / 'wechat'))

    # ==================== 文件限制 ====================
    MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', 20))
    MAX_FILE_SIZE_BYTES = MAX_FILE_SIZE_MB * 1024 * 1024
    MAX_PDF_PAGES = int(os.getenv('MAX_PDF_PAGES', 50))
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf', 'bmp', 'tiff'}
    ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'tiff'}
    ALLOWED_PDF_EXTENSIONS = {'pdf'}

    # ==================== 并发控制 ====================
    MAX_CONCURRENT_TASKS = int(os.getenv('MAX_CONCURRENT_TASKS', 3))

    # ==================== 临时文件配置 ====================
    TEMP_DIR = Path(os.getenv('TEMP_DIR', str(BASE_DIR / 'temp')))
    CLEANUP_TEMP_FILES = os.getenv('CLEANUP_TEMP_FILES', 'true').lower() == 'true'
    TEMP_FILE_MAX_AGE_HOURS = int(os.getenv('TEMP_FILE_MAX_AGE_HOURS', 24))

    # ==================== 预处理默认参数 ====================
    # 水印去除
    DEFAULT_WATERMARK_TOLERANCE = int(os.getenv('WATERMARK_TOLERANCE', 40))
    DEFAULT_WATERMARK_AUTO_DETECT = os.getenv('WATERMARK_AUTO_DETECT', 'true').lower() == 'true'

    # 图片纠偏
    DEFAULT_DESKEW_THRESHOLD = float(os.getenv('DESKEW_THRESHOLD', 1.0))  # 只有倾斜角度 > 1° 才纠正

    # ==================== PDF处理策略 ====================
    # 文本提取阈值
    MIN_TEXT_LENGTH_FOR_EXTRACTION = int(os.getenv('MIN_TEXT_LENGTH', 50))  # 最少字符数
    MAX_IMAGE_COVERAGE_FOR_TEXT = float(os.getenv('MAX_IMAGE_COVERAGE_TEXT', 0.3))  # 图片覆盖率上限

    # 整页渲染阈值
    MIN_IMAGE_COVERAGE_FULL_PAGE = float(os.getenv('MIN_IMAGE_COVERAGE_FULL', 0.8))  # 单图覆盖率下限

    # 渲染质量
    PDF_RENDER_SCALE = float(os.getenv('PDF_RENDER_SCALE', 2.0))  # 渲染缩放倍数，提高清晰度

    # ==================== 日志配置 ====================
    LOG_LEVEL = os.getenv('LOG_LEVEL', 'INFO').upper()
    LOG_FORMAT = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    LOG_FILE = os.getenv('LOG_FILE', str(BASE_DIR / 'logs' / 'app.log'))

    # ==================== API响应配置 ====================
    JSON_AS_ASCII = False  # 支持中文字符
    JSON_SORT_KEYS = False

    @classmethod
    def init_app(cls):
        """初始化应用环境"""
        # 创建必要的目录
        cls.TEMP_DIR.mkdir(parents=True, exist_ok=True)

        # 创建日志目录
        log_dir = Path(cls.LOG_FILE).parent
        log_dir.mkdir(parents=True, exist_ok=True)

        return cls

    @classmethod
    def get_summary(cls):
        """获取配置摘要（用于日志）"""
        return {
            'host': cls.HOST,
            'port': cls.PORT,
            'debug': cls.DEBUG,
            'max_file_size_mb': cls.MAX_FILE_SIZE_MB,
            'max_concurrent_tasks': cls.MAX_CONCURRENT_TASKS,
            'temp_dir': str(cls.TEMP_DIR),
            'log_level': cls.LOG_LEVEL,
        }


class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    LOG_LEVEL = 'DEBUG'


class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    LOG_LEVEL = 'WARNING'


# 配置字典
config = {
    'development': DevelopmentConfig,
    'production': ProductionConfig,
    'default': Config
}


def get_config(env=None):
    """获取配置对象"""
    if env is None:
        env = os.getenv('FLASK_ENV', 'default')
    return config.get(env, Config)
