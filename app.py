"""
Flask应用入口
"""
from flask import Flask
from config.settings import get_config, Config
from utils.logger import setup_logger, get_logger
from api.routes import api_bp
from api.error_handlers import register_error_handlers


def create_app(config_name=None):
    """
    应用工厂函数

    Args:
        config_name: 配置名称 ('development', 'production', 'default')

    Returns:
        Flask: Flask应用实例
    """
    app = Flask(__name__, static_folder='static', static_url_path='/static')

    # 加载配置
    config_class = get_config(config_name)
    app.config.from_object(config_class)

    # 初始化配置（创建必要的目录）
    config_class.init_app()

    # 设置日志
    logger = setup_logger(
        name='wxocr',
        log_file=config_class.LOG_FILE,
        log_level=config_class.LOG_LEVEL,
        log_format=config_class.LOG_FORMAT
    )

    logger.info("=" * 60)
    logger.info("启动 WeChat OCR 服务")
    logger.info("=" * 60)
    logger.info(f"配置摘要: {config_class.get_summary()}")

    # 初始化微信OCR
    try:
        import wcocr
        wcocr.init(config_class.WCOCR_BIN_PATH, config_class.WCOCR_LIB_PATH)
        app.config['WCOCR_AVAILABLE'] = True
        logger.info(f"微信OCR初始化成功: {config_class.WCOCR_BIN_PATH}")
    except Exception as e:
        app.config['WCOCR_AVAILABLE'] = False
        logger.warning(f"微信OCR初始化失败（进入测试模式）: {e}")
        logger.warning("⚠️  服务将以测试模式运行，OCR接口将返回模拟数据")

    # 注册蓝图
    app.register_blueprint(api_bp)
    logger.info("API蓝图注册成功")

    # 注册错误处理器
    register_error_handlers(app)
    logger.info("错误处理器注册成功")

    # 设置JSON配置
    app.config['JSON_AS_ASCII'] = config_class.JSON_AS_ASCII
    app.config['JSON_SORT_KEYS'] = config_class.JSON_SORT_KEYS

    # 添加根路由和静态页面
    @app.route('/')
    @app.route('/index.html')
    def index():
        """主页 - OCR Web 界面"""
        from flask import send_from_directory
        return send_from_directory('static', 'index.html')

    @app.route('/app.js')
    def app_js():
        """Vue应用脚本"""
        from flask import send_from_directory
        return send_from_directory('static', 'app.js')

    logger.info("应用创建完成")
    return app


if __name__ == '__main__':
    # 创建应用
    app = create_app()

    # 获取配置
    config = get_config()

    # 运行应用
    logger = get_logger(__name__)
    logger.info(f"服务启动在 http://{config.HOST}:{config.PORT}")

    app.run(
        host=config.HOST,
        port=config.PORT,
        debug=config.DEBUG,
        threaded=True
    )
