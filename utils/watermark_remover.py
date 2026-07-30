"""
水印去除工具

提供两种水印去除方式：
1. 指定色值去除（精确、快速）
2. 自动识别去除（灵活、但可能误判）
"""
import cv2
import numpy as np
from typing import Optional, Tuple
from utils.logger import get_logger

logger = get_logger(__name__)


def remove_by_color(image: np.ndarray, watermark_color: Tuple[int, int, int],
                   tolerance: int = 40) -> np.ndarray:
    """
    根据指定颜色去除水印

    Args:
        image: 图片数组 (BGR格式)
        watermark_color: 水印颜色 (R, G, B)
        tolerance: 颜色容差 (0-255)

    Returns:
        np.ndarray: 处理后的图片
    """
    try:
        # 转换颜色格式 RGB -> BGR (OpenCV使用BGR)
        watermark_bgr = (watermark_color[2], watermark_color[1], watermark_color[0])

        # 计算每个像素与水印颜色的欧氏距离
        watermark_array = np.array(watermark_bgr, dtype=np.float64)
        diff = image.astype(np.float64) - watermark_array
        distance = np.sqrt(np.sum(diff ** 2, axis=2))

        # 创建掩码：距离小于容差的像素认为是水印
        mask = distance <= tolerance

        # 将水印像素替换为白色
        result = image.copy()
        result[mask] = [255, 255, 255]

        removed_pixels = np.sum(mask)
        total_pixels = mask.size
        removal_rate = removed_pixels / total_pixels

        logger.info(f"按颜色去水印完成: 移除 {removal_rate:.2%} 的像素")

        return result

    except Exception as e:
        logger.error(f"按颜色去水印失败: {e}")
        raise


def auto_detect_watermark(image: np.ndarray, saturation_thresh: int = 40,
                          lightness_thresh: int = 190) -> np.ndarray:
    """
    自动检测水印区域（基于HSV特征）

    水印通常的特征：
    - 高亮度（接近白色）
    - 低饱和度（浅色调）
    - 非纯白背景

    Args:
        image: 图片数组 (BGR格式)
        saturation_thresh: 饱和度阈值 (0-255，越低越浅)
        lightness_thresh: 亮度阈值 (0-255，越高越亮)

    Returns:
        np.ndarray: 二值掩码 (255=水印, 0=非水印)
    """
    try:
        # 转换到HSV色彩空间
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        h, s, v = cv2.split(hsv)

        # 检测特征：高亮度 + 低饱和度，但非纯白
        mask = ((v > lightness_thresh) & (v < 253) &
                (s < saturation_thresh) & (s > 5)).astype(np.uint8) * 255

        # 形态学操作：去除孤立噪点，连接水印区域
        kernel = np.ones((3, 3), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_CLOSE, kernel, iterations=2)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel, iterations=1)

        detected_pixels = np.sum(mask > 0)
        total_pixels = mask.size
        detection_rate = detected_pixels / total_pixels

        logger.info(f"自动检测水印完成: 检测到 {detection_rate:.2%} 的像素")

        return mask

    except Exception as e:
        logger.error(f"自动检测水印失败: {e}")
        raise


def remove_watermark_by_inpainting(image: np.ndarray, mask: np.ndarray,
                                   inpaint_radius: int = 3) -> np.ndarray:
    """
    使用图像修复算法去除水印

    比直接涂白更自然，能保留边缘和纹理

    Args:
        image: 图片数组 (BGR格式)
        mask: 水印掩码 (255=水印, 0=非水印)
        inpaint_radius: 修复半径

    Returns:
        np.ndarray: 修复后的图片
    """
    try:
        # 使用 Telea 算法进行修复
        result = cv2.inpaint(image, mask, inpaint_radius, cv2.INPAINT_TELEA)

        logger.debug("图像修复完成")
        return result

    except Exception as e:
        logger.error(f"图像修复失败: {e}")
        raise


def remove_watermark(image: np.ndarray,
                    watermark_color: Optional[Tuple[int, int, int]] = None,
                    tolerance: int = 40,
                    use_inpainting: bool = False) -> np.ndarray:
    """
    去除水印（统一入口）

    Args:
        image: 图片数组 (BGR格式)
        watermark_color: 水印颜色 (R, G, B)，None表示自动检测
        tolerance: 颜色容差 (0-255)
        use_inpainting: 是否使用修复算法（更自然但更慢）

    Returns:
        np.ndarray: 处理后的图片
    """
    logger.info(f"开始去除水印: 颜色={'指定' if watermark_color else '自动'}, "
               f"修复={'是' if use_inpainting else '否'}")

    if watermark_color:
        # 方式1: 指定色值去除
        if use_inpainting:
            # 先生成掩码，再用修复算法
            watermark_bgr = (watermark_color[2], watermark_color[1], watermark_color[0])
            watermark_array = np.array(watermark_bgr, dtype=np.float64)
            diff = image.astype(np.float64) - watermark_array
            distance = np.sqrt(np.sum(diff ** 2, axis=2))
            mask = (distance <= tolerance).astype(np.uint8) * 255
            return remove_watermark_by_inpainting(image, mask)
        else:
            # 直接涂白
            return remove_by_color(image, watermark_color, tolerance)
    else:
        # 方式2: 自动检测去除
        mask = auto_detect_watermark(image)

        if use_inpainting:
            return remove_watermark_by_inpainting(image, mask)
        else:
            # 直接涂白
            result = image.copy()
            result[mask > 0] = [255, 255, 255]
            return result


def preprocess_for_ocr(image: np.ndarray, binary_threshold: int = 150) -> np.ndarray:
    """
    针对OCR的图片预处理（二值化增强）

    将图片转为黑白二值图，最大化文字与背景的对比度

    Args:
        image: 图片数组 (BGR格式)
        binary_threshold: 二值化阈值 (0-255)

    Returns:
        np.ndarray: 二值化后的图片
    """
    try:
        # 转灰度
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # 归一化（增强对比度）
        normalized = cv2.normalize(gray, None, 0, 255, cv2.NORM_MINMAX)

        # 二值化
        _, binary = cv2.threshold(normalized, binary_threshold, 255, cv2.THRESH_BINARY)

        # 转回BGR（保持格式一致）
        result = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)

        logger.debug("OCR预处理完成（二值化）")
        return result

    except Exception as e:
        logger.error(f"OCR预处理失败: {e}")
        raise
