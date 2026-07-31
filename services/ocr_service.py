"""
OCR服务封装

封装对 wcocr 的调用，提供统一的接口和错误处理
"""
from typing import List, Dict, Optional
from utils.logger import get_logger
from api.error_handlers import OcrProcessError

logger = get_logger(__name__)


class OcrResult:
    """OCR识别结果"""
    def __init__(self):
        self.text = ""  # 纯文本
        self.details = []  # 详细结果（位置、置信度等）
        self.confidence = 0.0  # 平均置信度
        self.success = False
        self.width = 0  # 图片宽度
        self.height = 0  # 图片高度
        self.image_path = ""  # 图片路径


def ocr_image(image_path: str) -> OcrResult:
    """
    对单张图片执行OCR识别

    Args:
        image_path: 图片路径

    Returns:
        OcrResult: 识别结果
    """
    result = OcrResult()

    try:
        import wcocr

        logger.info(f"执行OCR识别: {image_path}")

        # 调用 wcocr
        ocr_response = wcocr.ocr(image_path)

        # 解析结果
        if isinstance(ocr_response, dict):
            # 提取文本
            ocr_data = ocr_response.get('ocr_response', [])

            text_parts = []
            confidences = []

            for item in ocr_data:
                text = item.get('text', '').strip()
                if text:
                    text_parts.append(text)
                    confidences.append(item.get('rate', 0.0))

            result.text = '\n'.join(text_parts)
            result.details = ocr_data
            result.confidence = sum(confidences) / len(confidences) if confidences else 0.0
            result.width = ocr_response.get('width', 0)
            result.height = ocr_response.get('height', 0)
            result.image_path = ocr_response.get('image_path', image_path)
            result.success = True

            logger.info(f"OCR识别成功: 识别到 {len(text_parts)} 个文本块, "
                       f"平均置信度: {result.confidence:.2%}")

        else:
            logger.warning(f"OCR返回格式异常: {type(ocr_response)}")
            result.success = False

        return result

    except ImportError:
        logger.error("wcocr 模块未安装或初始化失败")
        raise OcrProcessError("OCR引擎不可用", None)
    except Exception as e:
        logger.error(f"OCR识别失败: {e}", exc_info=True)
        raise OcrProcessError(f"OCR识别失败: {str(e)}", e)


def ocr_images_batch(image_paths: List[str]) -> List[OcrResult]:
    """
    批量识别多张图片

    Args:
        image_paths: 图片路径列表

    Returns:
        List[OcrResult]: 识别结果列表
    """
    results = []

    logger.info(f"开始批量OCR识别: {len(image_paths)} 张图片")

    for i, image_path in enumerate(image_paths, 1):
        try:
            logger.debug(f"处理第 {i}/{len(image_paths)} 张图片")
            result = ocr_image(image_path)
            results.append(result)
        except Exception as e:
            logger.error(f"第 {i} 张图片识别失败: {e}")
            # 创建失败结果
            failed_result = OcrResult()
            failed_result.success = False
            results.append(failed_result)

    successful = sum(1 for r in results if r.success)
    logger.info(f"批量OCR完成: 成功 {successful}/{len(image_paths)}")

    return results


def combine_ocr_results(results: List[OcrResult], separator: str = '\n\n') -> str:
    """
    合并多个OCR结果为单个文本

    Args:
        results: OCR结果列表
        separator: 分隔符

    Returns:
        str: 合并后的文本
    """
    text_parts = [r.text for r in results if r.success and r.text.strip()]
    return separator.join(text_parts)


def get_ocr_statistics(results: List[OcrResult]) -> Dict:
    """
    获取OCR识别的统计信息

    Args:
        results: OCR结果列表

    Returns:
        dict: 统计信息
    """
    successful = [r for r in results if r.success]

    return {
        'total_images': len(results),
        'successful': len(successful),
        'failed': len(results) - len(successful),
        'total_text_length': sum(len(r.text) for r in successful),
        'average_confidence': sum(r.confidence for r in successful) / len(successful) if successful else 0.0,
    }
