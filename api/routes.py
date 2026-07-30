"""
API路由定义
"""
from flask import Blueprint, request, jsonify
from api.validators import validate_file_upload, OcrRequestParams, ValidationError, is_pdf, is_image
from api.error_handlers import error_response, RateLimitError
from utils.logger import get_logger
from pathlib import Path
import time
import os
import uuid

logger = get_logger(__name__)

# 创建蓝图
api_bp = Blueprint('api', __name__, url_prefix='/api/v1')


@api_bp.route('/health', methods=['GET'])
def health_check():
    """健康检查接口"""
    return jsonify({
        'success': True,
        'status': 'healthy',
        'timestamp': int(time.time() * 1000)
    })


@api_bp.route('/ocr', methods=['POST'])
@validate_file_upload
def ocr():
    """
    OCR识别接口

    接收图片或PDF文件，返回识别的文本内容

    Returns:
        JSON响应
    """
    from flask import current_app
    start_time = time.time()

    try:
        # 解析请求参数
        params = OcrRequestParams()
        logger.info(f"收到OCR请求: {params.to_dict()}")

        # 检查是否为测试模式
        wcocr_available = current_app.config.get('WCOCR_AVAILABLE', False)

        if not wcocr_available:
            # 测试模式：返回模拟数据
            logger.info("⚠️  测试模式：返回模拟OCR结果")

            file = request.files['file']
            filename = file.filename

            # 根据文件类型生成不同的模拟数据
            from api.validators import is_pdf, is_image

            if is_pdf(filename):
                mock_text = "【模拟PDF识别结果】\n\n这是第一页的内容。\n包含一些示例文字用于测试。\n\n这是第二页的内容。\n更多测试文字。"
                file_type = 'pdf'
                page_count = 2
                processing_method = 'text_extraction'
            elif is_image(filename):
                mock_text = "【模拟图片识别结果】\n这是图片中的示例文字\n用于测试OCR接口"
                file_type = 'image'
                page_count = 1
                processing_method = 'full_page_render'
            else:
                mock_text = "【未知文件类型】"
                file_type = 'unknown'
                page_count = 0
                processing_method = 'unknown'

            result = {
                'success': True,
                'data': {
                    'text': mock_text,
                    'metadata': {
                        'file_type': file_type,
                        'page_count': page_count,
                        'processing_method': processing_method,
                        'preprocessed': {
                            'watermark_removed': params.remove_watermark,
                            'deskewed': params.deskew
                        },
                        'processing_time_ms': int((time.time() - start_time) * 1000),
                        'test_mode': True
                    }
                }
            }
        else:
            # 生产模式：实际的OCR处理逻辑
            result = process_ocr_request(params, start_time)

        logger.info(f"OCR处理完成，耗时: {result['data']['metadata']['processing_time_ms']}ms")
        return jsonify(result)

    except ValidationError as e:
        # 验证错误会被全局错误处理器捕获
        raise
    except RateLimitError as e:
        # 限流错误会被全局错误处理器捕获
        raise
    except Exception as e:
        logger.error(f"OCR处理失败: {str(e)}", exc_info=True)
        return error_response(500, 'OCR_FAILED', f'OCR处理失败: {str(e)}')


@api_bp.route('/ocr', methods=['GET', 'PUT', 'DELETE', 'PATCH'])
def ocr_unsupported_method():
    """处理不支持的HTTP方法"""
    return error_response(405, 'METHOD_NOT_ALLOWED', '仅支持POST方法')


# 添加请求日志中间件
@api_bp.before_request
def log_request():
    """记录请求日志"""
    logger.debug(f"收到请求: {request.method} {request.path}")
    logger.debug(f"请求头: {dict(request.headers)}")


@api_bp.after_request
def log_response(response):
    """记录响应日志"""
    logger.debug(f"响应状态: {response.status_code}")
    return response


def process_ocr_request(params: OcrRequestParams, start_time: float) -> dict:
    """
    处理OCR请求的主逻辑

    Args:
        params: 请求参数
        start_time: 开始时间

    Returns:
        dict: 响应数据
    """
    from config.settings import Config
    from services.task_manager import get_task_manager
    from services.pdf_processor import process_pdf
    from services.image_processor import preprocess_image
    from services.ocr_service import ocr_image, ocr_images_batch, combine_ocr_results

    temp_files = []  # 记录所有临时文件，最后清理

    try:
        # 获取任务管理器并检查限流
        task_manager = get_task_manager()

        with task_manager.task_slot():
            # 保存上传的文件
            file = request.files['file']
            filename = file.filename
            file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''

            # 生成临时文件路径
            temp_dir = Config.TEMP_DIR
            temp_dir.mkdir(parents=True, exist_ok=True)

            input_filename = f"{uuid.uuid4()}.{file_ext}"
            input_path = temp_dir / input_filename
            file.save(str(input_path))
            temp_files.append(input_path)

            logger.info(f"文件已保存: {input_path}")

            # 判断文件类型
            if is_pdf(filename):
                # PDF处理流程
                final_text, metadata = process_pdf_file(
                    str(input_path),
                    params,
                    temp_files
                )
                file_type = 'pdf'

            elif is_image(filename):
                # 图片处理流程
                final_text, metadata = process_image_file(
                    str(input_path),
                    params,
                    temp_files
                )
                file_type = 'image'

            else:
                raise ValueError(f"不支持的文件类型: {file_ext}")

            # 构建响应
            result = {
                'success': True,
                'data': {
                    'text': final_text,
                    'metadata': {
                        'file_type': file_type,
                        'page_count': metadata.get('page_count', 1),
                        'processing_method': metadata.get('processing_method', 'unknown'),
                        'preprocessed': metadata.get('preprocessed', {}),
                        'processing_time_ms': int((time.time() - start_time) * 1000),
                        'test_mode': False
                    }
                }
            }

            return result

    finally:
        # 清理临时文件
        if Config.CLEANUP_TEMP_FILES:
            cleanup_temp_files(temp_files)


def process_pdf_file(pdf_path: str, params: OcrRequestParams, temp_files: list) -> tuple:
    """
    处理PDF文件

    Args:
        pdf_path: PDF文件路径
        params: 请求参数
        temp_files: 临时文件列表（用于记录需要清理的文件）

    Returns:
        tuple: (文本内容, 元数据)
    """
    from services.pdf_processor import process_pdf
    from services.image_processor import preprocess_image
    from services.ocr_service import ocr_images_batch, combine_ocr_results

    logger.info("开始处理PDF文件")

    # 处理PDF
    pdf_result = process_pdf(pdf_path)

    # 收集所有需要OCR的图片
    images_to_ocr = pdf_result.images.copy()

    # 如果需要预处理
    if params.remove_watermark or params.deskew:
        logger.info("对提取的图片进行预处理")
        preprocessed_images = []

        for img_path in images_to_ocr:
            output_path = f"{img_path}_processed.png"
            preprocessed_path, preprocess_stats = preprocess_image(
                img_path,
                output_path,
                remove_watermark=params.remove_watermark,
                watermark_color=params.watermark_color,
                watermark_tolerance=params.watermark_tolerance,
                deskew=params.deskew
            )
            preprocessed_images.append(preprocessed_path)
            temp_files.append(Path(preprocessed_path))

        images_to_ocr = preprocessed_images

    # OCR识别
    if images_to_ocr:
        logger.info(f"对 {len(images_to_ocr)} 张图片执行OCR")
        ocr_results = ocr_images_batch(images_to_ocr)
        ocr_text = combine_ocr_results(ocr_results)
    else:
        ocr_text = ""

    # 合并文本
    if pdf_result.text and ocr_text:
        final_text = pdf_result.text + "\n\n" + ocr_text
    elif pdf_result.text:
        final_text = pdf_result.text
    else:
        final_text = ocr_text

    # 元数据
    metadata = {
        'page_count': pdf_result.page_count,
        'processing_method': pdf_result.strategy,
        'preprocessed': {
            'watermark_removed': params.remove_watermark,
            'deskewed': params.deskew
        }
    }

    # 将PDF提取的图片加入清理列表
    for img_path in pdf_result.images:
        temp_files.append(Path(img_path))

    return final_text, metadata


def process_image_file(image_path: str, params: OcrRequestParams, temp_files: list) -> tuple:
    """
    处理图片文件

    Args:
        image_path: 图片文件路径
        params: 请求参数
        temp_files: 临时文件列表

    Returns:
        tuple: (文本内容, 元数据)
    """
    from services.image_processor import preprocess_image
    from services.ocr_service import ocr_image

    logger.info("开始处理图片文件")

    # 预处理
    if params.remove_watermark or params.deskew:
        logger.info("对图片进行预处理")
        processed_path = f"{image_path}_processed.png"
        processed_image, preprocess_stats = preprocess_image(
            image_path,
            processed_path,
            remove_watermark=params.remove_watermark,
            watermark_color=params.watermark_color,
            watermark_tolerance=params.watermark_tolerance,
            deskew=params.deskew
        )
        temp_files.append(Path(processed_path))
        ocr_input = processed_path
    else:
        ocr_input = image_path

    # OCR识别
    logger.info("执行OCR识别")
    ocr_result = ocr_image(ocr_input)

    # 元数据
    metadata = {
        'page_count': 1,
        'processing_method': 'full_page_render',
        'preprocessed': {
            'watermark_removed': params.remove_watermark,
            'deskewed': params.deskew
        }
    }

    return ocr_result.text, metadata


def cleanup_temp_files(temp_files: list):
    """
    清理临时文件

    Args:
        temp_files: 临时文件路径列表
    """
    for file_path in temp_files:
        try:
            if isinstance(file_path, (str, Path)):
                file_path = Path(file_path)
                if file_path.exists():
                    file_path.unlink()
                    logger.debug(f"已清理临时文件: {file_path}")
        except Exception as e:
            logger.warning(f"清理临时文件失败 {file_path}: {e}")
