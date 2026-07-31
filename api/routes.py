"""
API路由定义
"""
from flask import Blueprint, request, jsonify
from api.validators import validate_file_upload, OcrRequestParams, ValidationError, is_pdf, is_image
from api.error_handlers import error_response, RateLimitError
from api.auth import require_api_key
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
@require_api_key
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
                    'width': 800,
                    'height': 600,
                    'imgpath': 'temp/test_mode.png',
                    'ocr_response': [
                        {
                            'text': '【模拟图片识别结果】',
                            'rate': 0.95,
                            'left': 10.0,
                            'top': 10.0,
                            'right': 300.0,
                            'bottom': 40.0
                        },
                        {
                            'text': '这是图片中的示例文字',
                            'rate': 0.93,
                            'left': 10.0,
                            'top': 50.0,
                            'right': 280.0,
                            'bottom': 80.0
                        }
                    ],
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

            # 如果是 PDF 文件，使用按页组织的数据
            if 'pages' in metadata:
                result['data']['pages'] = metadata['pages']
                result['data']['pdfpath'] = str(input_path)  # 返回 PDF 路径
            else:
                # 图片文件，使用单页格式
                result['data']['width'] = metadata.get('width', 0)
                result['data']['height'] = metadata.get('height', 0)
                result['data']['imgpath'] = str(input_path)  # 返回图片路径
                result['data']['ocr_response'] = metadata.get('ocr_response', [])

            # 清理旧的临时文件（保留最近30个）
            cleanup_old_temp_files(temp_dir, keep_recent=30)

            return result

    finally:
        # 不再立即清理临时文件，改为保留供后续 embed 使用
        pass


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
    from services.ocr_service import ocr_image

    logger.info("开始处理PDF文件")

    # 处理PDF
    pdf_result = process_pdf(pdf_path)

    # 为每页执行 OCR（如果需要）
    for page_info in pdf_result.pages:
        if page_info.image_path:
            # 该页需要 OCR
            img_path = page_info.image_path

            # 预处理
            if params.remove_watermark or params.deskew:
                logger.info(f"对第 {page_info.page_number} 页图片进行预处理")
                processed_path = f"{img_path}_processed.png"
                processed_image, preprocess_stats = preprocess_image(
                    img_path,
                    processed_path,
                    remove_watermark=params.remove_watermark,
                    watermark_color=params.watermark_color,
                    watermark_tolerance=params.watermark_tolerance,
                    deskew=params.deskew
                )
                temp_files.append(Path(processed_path))
                ocr_input = processed_path
            else:
                ocr_input = img_path

            # OCR 识别
            logger.info(f"对第 {page_info.page_number} 页执行 OCR")
            ocr_result = ocr_image(ocr_input)

            # 将 OCR 结果存入页面信息
            if ocr_result.success:
                # 如果该页已有提取的文本，追加 OCR 结果
                if page_info.text:
                    page_info.text += "\n\n" + ocr_result.text
                else:
                    page_info.text = ocr_result.text

                page_info.ocr_response = ocr_result.details
                # 如果 OCR 结果中有宽高，使用 OCR 的
                if ocr_result.width > 0:
                    page_info.width = ocr_result.width
                    page_info.height = ocr_result.height

    # 合并所有页的文本
    all_text_parts = [p.text for p in pdf_result.pages if p.text]
    final_text = '\n\n'.join(all_text_parts) if all_text_parts else ""

    # 构建按页组织的数据
    pages_data = []
    for page_info in pdf_result.pages:
        pages_data.append({
            'page_number': page_info.page_number,
            'width': page_info.width,
            'height': page_info.height,
            'text': page_info.text,
            'strategy': page_info.strategy,
            'ocr_response': page_info.ocr_response
        })

    # 元数据
    metadata = {
        'page_count': pdf_result.page_count,
        'processing_method': pdf_result.strategy,
        'preprocessed': {
            'watermark_removed': params.remove_watermark,
            'deskewed': params.deskew
        },
        'pages': pages_data
    }

    # 将PDF提取的图片加入清理列表
    for img_path in pdf_result.images:
        temp_files.append(Path(img_path))

    return final_text, metadata

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
        },
        # 添加详细信息
        'width': ocr_result.width,
        'height': ocr_result.height,
        'imgpath': ocr_result.imgpath,
        'ocr_response': ocr_result.details
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


def cleanup_old_temp_files(temp_dir: Path, keep_recent: int = 30):
    """
    清理旧的临时文件，保留最近的N个文件

    Args:
        temp_dir: 临时文件目录
        keep_recent: 保留最近的文件数量
    """
    try:
        if not temp_dir.exists():
            return

        # 获取所有文件并按修改时间排序
        files = []
        for file_path in temp_dir.iterdir():
            if file_path.is_file():
                files.append((file_path, file_path.stat().st_mtime))

        # 按修改时间降序排序
        files.sort(key=lambda x: x[1], reverse=True)

        # 删除超过保留数量的文件
        if len(files) > keep_recent:
            files_to_delete = files[keep_recent:]
            for file_path, _ in files_to_delete:
                try:
                    file_path.unlink()
                    logger.debug(f"已清理旧临时文件: {file_path}")
                except Exception as e:
                    logger.warning(f"清理旧临时文件失败 {file_path}: {e}")

            logger.info(f"已清理 {len(files_to_delete)} 个旧临时文件，保留最近 {keep_recent} 个")

    except Exception as e:
        logger.error(f"清理旧临时文件时出错: {e}")


@api_bp.route('/embed', methods=['POST'])
@require_api_key
def embed_text_to_pdf():
    """
    将OCR文本块嵌入到图片或PDF中，生成新的PDF文件

    请求体（JSON）:
    {
        "file_path": "temp/xxx.png" or "temp/xxx.pdf",
        "file_type": "image" or "pdf",
        "ocr_response": [...],  // 图片模式
        "pages": [...]  // PDF模式
    }

    Returns:
        PDF文件下载
    """
    from flask import send_file
    from config.settings import Config
    from services.pdf_embedder import embed_text_to_image, embed_text_to_pdf

    try:
        data = request.get_json()

        if not data:
            return error_response(400, 'INVALID_REQUEST', '请求体不能为空')

        file_path = data.get('file_path')
        file_type = data.get('file_type')

        if not file_path:
            return error_response(400, 'MISSING_FILE_PATH', '缺少 file_path 参数')

        # 检查文件是否存在
        full_path = Path(file_path)
        if not full_path.is_absolute():
            full_path = Config.TEMP_DIR / file_path

        if not full_path.exists():
            return error_response(404, 'FILE_NOT_FOUND',
                '临时文件已过期或不存在，请重新上传文件进行OCR识别')

        # 生成输出PDF路径
        output_filename = f"{uuid.uuid4()}_embedded.pdf"
        output_path = Config.TEMP_DIR / output_filename

        # 根据文件类型处理
        if file_type == 'image':
            ocr_response = data.get('ocr_response', [])
            if not ocr_response:
                return error_response(400, 'MISSING_OCR_DATA', '缺少 ocr_response 数据')

            logger.info(f"嵌入文本到图片: {full_path}")
            embed_text_to_image(str(full_path), ocr_response, str(output_path))

        elif file_type == 'pdf':
            pages = data.get('pages', [])
            if not pages:
                return error_response(400, 'MISSING_PAGES_DATA', '缺少 pages 数据')

            logger.info(f"嵌入文本到PDF: {full_path}")
            embed_text_to_pdf(str(full_path), pages, str(output_path))

        else:
            return error_response(400, 'INVALID_FILE_TYPE',
                f'不支持的文件类型: {file_type}')

        # 返回PDF文件
        return send_file(
            str(output_path),
            as_attachment=True,
            download_name=f"ocr_embedded_{int(time.time())}.pdf",
            mimetype='application/pdf'
        )

    except Exception as e:
        logger.error(f"嵌入文本失败: {str(e)}", exc_info=True)
        return error_response(500, 'EMBED_FAILED', f'嵌入文本失败: {str(e)}')
