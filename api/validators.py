"""
请求参数验证器
"""
from functools import wraps
from flask import request, jsonify
from werkzeug.datastructures import FileStorage
from config.settings import Config
from utils.logger import get_logger

logger = get_logger(__name__)


class ValidationError(Exception):
    """参数验证错误"""
    def __init__(self, message, code='VALIDATION_ERROR'):
        self.message = message
        self.code = code
        super().__init__(self.message)


def validate_file_upload(f):
    """
    验证文件上传的装饰器

    检查：
    - 文件是否存在
    - 文件扩展名
    - 文件大小
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # 检查是否有文件
        if 'file' not in request.files:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'NO_FILE',
                    'message': '请求中未找到文件'
                }
            }), 400

        file = request.files['file']

        # 检查文件名是否为空
        if file.filename == '':
            return jsonify({
                'success': False,
                'error': {
                    'code': 'EMPTY_FILENAME',
                    'message': '文件名为空'
                }
            }), 400

        # 检查文件扩展名
        if not allowed_file(file.filename):
            return jsonify({
                'success': False,
                'error': {
                    'code': 'INVALID_FILE_TYPE',
                    'message': f'不支持的文件类型，仅支持: {", ".join(Config.ALLOWED_EXTENSIONS)}'
                }
            }), 400

        # 检查文件大小（通过读取内容长度）
        file.seek(0, 2)  # 移动到文件末尾
        file_size = file.tell()
        file.seek(0)  # 重置到开头

        if file_size > Config.MAX_FILE_SIZE_BYTES:
            return jsonify({
                'success': False,
                'error': {
                    'code': 'FILE_TOO_LARGE',
                    'message': f'文件大小超过限制 ({Config.MAX_FILE_SIZE_MB}MB)'
                }
            }), 413

        return f(*args, **kwargs)

    return decorated_function


def allowed_file(filename):
    """
    检查文件扩展名是否允许

    Args:
        filename: 文件名

    Returns:
        bool: 是否允许
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_EXTENSIONS


def is_pdf(filename):
    """
    判断是否为PDF文件

    Args:
        filename: 文件名

    Returns:
        bool: 是否为PDF
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_PDF_EXTENSIONS


def is_image(filename):
    """
    判断是否为图片文件

    Args:
        filename: 文件名

    Returns:
        bool: 是否为图片
    """
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in Config.ALLOWED_IMAGE_EXTENSIONS


def parse_bool_param(param_name, default=False):
    """
    解析布尔型参数

    Args:
        param_name: 参数名
        default: 默认值

    Returns:
        bool: 解析后的值
    """
    value = request.form.get(param_name, str(default)).lower()
    return value in ('true', '1', 'yes', 'on')


def parse_int_param(param_name, default=0, min_value=None, max_value=None):
    """
    解析整数参数

    Args:
        param_name: 参数名
        default: 默认值
        min_value: 最小值
        max_value: 最大值

    Returns:
        int: 解析后的值

    Raises:
        ValidationError: 参数无效
    """
    try:
        value = int(request.form.get(param_name, default))

        if min_value is not None and value < min_value:
            raise ValidationError(
                f'参数 {param_name} 不能小于 {min_value}',
                'PARAM_OUT_OF_RANGE'
            )

        if max_value is not None and value > max_value:
            raise ValidationError(
                f'参数 {param_name} 不能大于 {max_value}',
                'PARAM_OUT_OF_RANGE'
            )

        return value
    except ValueError:
        raise ValidationError(
            f'参数 {param_name} 必须是整数',
            'INVALID_PARAM_TYPE'
        )


def parse_float_param(param_name, default=0.0, min_value=None, max_value=None):
    """
    解析浮点数参数

    Args:
        param_name: 参数名
        default: 默认值
        min_value: 最小值
        max_value: 最大值

    Returns:
        float: 解析后的值

    Raises:
        ValidationError: 参数无效
    """
    try:
        value = float(request.form.get(param_name, default))

        if min_value is not None and value < min_value:
            raise ValidationError(
                f'参数 {param_name} 不能小于 {min_value}',
                'PARAM_OUT_OF_RANGE'
            )

        if max_value is not None and value > max_value:
            raise ValidationError(
                f'参数 {param_name} 不能大于 {max_value}',
                'PARAM_OUT_OF_RANGE'
            )

        return value
    except ValueError:
        raise ValidationError(
            f'参数 {param_name} 必须是数字',
            'INVALID_PARAM_TYPE'
        )


def parse_color_param(param_name, default=None):
    """
    解析颜色参数（支持 #RRGGBB 格式）

    Args:
        param_name: 参数名
        default: 默认值

    Returns:
        tuple: (R, G, B) 或 None

    Raises:
        ValidationError: 颜色格式无效
    """
    value = request.form.get(param_name, '').strip()

    if not value:
        return default

    # 支持 #RRGGBB 格式
    if value.startswith('#'):
        value = value[1:]

    if len(value) != 6:
        raise ValidationError(
            f'参数 {param_name} 格式无效，应为 #RRGGBB',
            'INVALID_COLOR_FORMAT'
        )

    try:
        r = int(value[0:2], 16)
        g = int(value[2:4], 16)
        b = int(value[4:6], 16)
        return (r, g, b)
    except ValueError:
        raise ValidationError(
            f'参数 {param_name} 包含无效的十六进制字符',
            'INVALID_COLOR_FORMAT'
        )


class OcrRequestParams:
    """OCR请求参数封装"""

    def __init__(self):
        """从 Flask request 中解析参数"""
        try:
            # 文件参数
            self.file = request.files.get('file')

            # 预处理参数 - 水印去除
            self.remove_watermark = parse_bool_param('remove_watermark', False)
            self.watermark_color = parse_color_param('watermark_color', None)
            self.watermark_tolerance = parse_int_param(
                'watermark_tolerance',
                default=Config.DEFAULT_WATERMARK_TOLERANCE,
                min_value=0,
                max_value=255
            )

            # 预处理参数 - 纠偏
            self.deskew = parse_bool_param('deskew', False)

            # 预处理参数 - 去噪
            self.denoise = parse_bool_param('denoise', False)
            self.denoise_method = request.form.get('denoise_method', 'median').lower()
            if self.denoise_method not in ('median', 'fastNlMeans', 'bilateral'):
                self.denoise_method = 'median'

            # 预处理参数 - 对比度增强
            self.enhance_contrast = parse_bool_param('enhance_contrast', False)
            self.contrast_method = request.form.get('contrast_method', 'clahe').lower()
            if self.contrast_method not in ('clahe', 'histogram'):
                self.contrast_method = 'clahe'

            # 预处理参数 - 二值化
            self.binarize = parse_bool_param('binarize', False)
            self.binarize_method = request.form.get('binarize_method', 'gaussian').lower()
            if self.binarize_method not in ('gaussian', 'otsu'):
                self.binarize_method = 'gaussian'

            # 预处理参数 - 锐化
            self.sharpen = parse_bool_param('sharpen', False)
            self.sharpen_strength = parse_float_param(
                'sharpen_strength',
                default=1.0,
                min_value=0.5,
                max_value=2.0
            )

            # 输出格式
            self.output_format = request.form.get('output_format', 'plain').lower()
            if self.output_format not in ('plain', 'structured'):
                raise ValidationError(
                    'output_format 必须是 plain 或 structured',
                    'INVALID_OUTPUT_FORMAT'
                )

        except ValidationError:
            raise
        except Exception as e:
            logger.error(f"解析请求参数失败: {e}")
            raise ValidationError(f'参数解析失败: {str(e)}')

    def to_dict(self):
        """转换为字典（用于日志）"""
        return {
            'filename': self.file.filename if self.file else None,
            'remove_watermark': self.remove_watermark,
            'watermark_color': self.watermark_color,
            'watermark_tolerance': self.watermark_tolerance,
            'deskew': self.deskew,
            'denoise': self.denoise,
            'denoise_method': self.denoise_method,
            'enhance_contrast': self.enhance_contrast,
            'contrast_method': self.contrast_method,
            'binarize': self.binarize,
            'binarize_method': self.binarize_method,
            'sharpen': self.sharpen,
            'sharpen_strength': self.sharpen_strength,
            'output_format': self.output_format,
        }
