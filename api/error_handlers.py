"""
统一错误处理模块
"""
from flask import jsonify
from utils.logger import get_logger
from api.validators import ValidationError

logger = get_logger(__name__)


class RateLimitError(Exception):
    """超出并发限制错误"""
    def __init__(self, message='超出并发限制', current_tasks=0, max_concurrent=0):
        self.message = message
        self.current_tasks = current_tasks
        self.max_concurrent = max_concurrent
        super().__init__(self.message)


class OcrProcessError(Exception):
    """OCR处理错误"""
    def __init__(self, message, original_error=None):
        self.message = message
        self.original_error = original_error
        super().__init__(self.message)


def error_response(status_code, error_code, message, details=None):
    """
    生成标准错误响应

    Args:
        status_code: HTTP状态码
        error_code: 错误代码
        message: 错误消息
        details: 额外的错误详情

    Returns:
        tuple: (response, status_code)
    """
    response = {
        'success': False,
        'error': {
            'code': error_code,
            'message': message
        }
    }

    if details:
        response['error']['details'] = details

    return jsonify(response), status_code


def register_error_handlers(app):
    """
    注册错误处理器

    Args:
        app: Flask应用实例
    """

    @app.errorhandler(ValidationError)
    def handle_validation_error(e):
        """处理参数验证错误"""
        logger.warning(f"参数验证失败: {e.message}")
        return error_response(400, e.code, e.message)

    @app.errorhandler(RateLimitError)
    def handle_rate_limit_error(e):
        """处理限流错误"""
        logger.warning(f"请求被限流: {e.message}")
        return error_response(
            429,
            'RATE_LIMIT_EXCEEDED',
            e.message,
            {
                'current_tasks': e.current_tasks,
                'max_concurrent': e.max_concurrent
            }
        )

    @app.errorhandler(OcrProcessError)
    def handle_ocr_error(e):
        """处理OCR处理错误"""
        logger.error(f"OCR处理失败: {e.message}", exc_info=e.original_error)
        return error_response(500, 'OCR_PROCESS_ERROR', e.message)

    @app.errorhandler(404)
    def handle_not_found(e):
        """处理404错误"""
        return error_response(404, 'NOT_FOUND', '请求的资源不存在')

    @app.errorhandler(405)
    def handle_method_not_allowed(e):
        """处理405错误"""
        return error_response(405, 'METHOD_NOT_ALLOWED', '不支持的HTTP方法')

    @app.errorhandler(413)
    def handle_request_entity_too_large(e):
        """处理413错误（文件过大）"""
        return error_response(413, 'FILE_TOO_LARGE', '上传的文件过大')

    @app.errorhandler(500)
    def handle_internal_error(e):
        """处理500错误"""
        logger.error(f"服务器内部错误: {str(e)}", exc_info=True)
        return error_response(500, 'INTERNAL_ERROR', '服务器内部错误')

    @app.errorhandler(Exception)
    def handle_unexpected_error(e):
        """处理未预期的错误"""
        logger.error(f"未预期的错误: {str(e)}", exc_info=True)
        return error_response(500, 'UNEXPECTED_ERROR', f'发生未预期的错误: {str(e)}')
