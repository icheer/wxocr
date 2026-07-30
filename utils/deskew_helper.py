"""
图片纠偏工具

检测并纠正扫描件的轻微倾斜
"""
import cv2
import numpy as np
from typing import Tuple
from utils.logger import get_logger
from config.settings import Config

logger = get_logger(__name__)


def detect_skew_angle(image: np.ndarray, min_angle: float = -10.0, max_angle: float = 10.0) -> float:
    """
    检测图片倾斜角度（基于轮廓分析）

    Args:
        image: 图片数组 (BGR格式)
        min_angle: 最小检测角度
        max_angle: 最大检测角度

    Returns:
        float: 倾斜角度（度），正值表示顺时针倾斜
    """
    try:
        # 转灰度
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)

        # 高斯模糊，减少噪声
        blurred = cv2.GaussianBlur(gray, (9, 9), 0)

        # 自适应二值化
        _, binary = cv2.threshold(blurred, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)

        # 形态学操作：膨胀，连接文字行
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (30, 5))
        dilated = cv2.dilate(binary, kernel, iterations=1)

        # 查找轮廓
        contours, _ = cv2.findContours(dilated, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)

        # 分析轮廓角度
        angles = []
        for contour in contours:
            # 过滤小轮廓
            if cv2.contourArea(contour) < 100:
                continue

            # 获取最小外接矩形
            rect = cv2.minAreaRect(contour)
            angle = rect[-1]

            # OpenCV的角度范围是[-90, 0)
            # 需要转换到[-45, 45]区间
            if angle < -45:
                angle = 90 + angle
            elif angle > 45:
                angle = angle - 90

            # 过滤异常角度
            if min_angle <= angle <= max_angle:
                angles.append(angle)

        if not angles:
            logger.info("未检测到有效轮廓，假设图片无倾斜")
            return 0.0

        # 使用中位数作为最终角度（比平均值更抗噪声）
        angles.sort()
        median_angle = angles[len(angles) // 2]

        logger.info(f"检测到倾斜角度: {median_angle:.2f}°（共{len(angles)}个样本）")

        return median_angle

    except Exception as e:
        logger.error(f"检测倾斜角度失败: {e}")
        return 0.0


def detect_skew_angle_simple(image: np.ndarray) -> float:
    """
    使用deskew库检测倾斜角度（更简单但需要额外依赖）

    Args:
        image: 图片数组 (BGR格式)

    Returns:
        float: 倾斜角度（度）
    """
    try:
        from skimage.color import rgb2gray
        from deskew import determine_skew

        # 转灰度
        if len(image.shape) == 3:
            gray = rgb2gray(image)
        else:
            gray = image

        # 检测角度
        angle = determine_skew(gray)

        logger.info(f"检测到倾斜角度（deskew库）: {angle:.2f}°")

        return angle

    except ImportError:
        logger.warning("deskew库未安装，使用OpenCV方法")
        return detect_skew_angle(image)
    except Exception as e:
        logger.error(f"deskew检测失败: {e}")
        return 0.0


def correct_skew(image: np.ndarray, angle: float, background_color: Tuple[int, int, int] = (255, 255, 255)) -> np.ndarray:
    """
    纠正图片倾斜

    Args:
        image: 图片数组 (BGR格式)
        angle: 倾斜角度（度）
        background_color: 填充背景色 (B, G, R)

    Returns:
        np.ndarray: 纠正后的图片
    """
    try:
        h, w = image.shape[:2]

        # 计算旋转中心
        center = (w / 2, h / 2)

        # 获取旋转矩阵
        rotation_matrix = cv2.getRotationMatrix2D(center, angle, 1.0)

        # 执行旋转
        rotated = cv2.warpAffine(
            image,
            rotation_matrix,
            (w, h),
            flags=cv2.INTER_LINEAR,
            borderMode=cv2.BORDER_CONSTANT,
            borderValue=background_color
        )

        logger.info(f"图片纠偏完成: 旋转{angle:.2f}°")

        return rotated

    except Exception as e:
        logger.error(f"图片纠偏失败: {e}")
        raise


def deskew_image(image: np.ndarray, threshold: float = None, use_simple: bool = False) -> Tuple[np.ndarray, float]:
    """
    检测并纠正图片倾斜（统一入口）

    Args:
        image: 图片数组 (BGR格式)
        threshold: 倾斜角度阈值（度），只有超过此值才纠正
        use_simple: 是否使用deskew库（更准确但需要额外依赖）

    Returns:
        Tuple[np.ndarray, float]: (纠正后的图片, 倾斜角度)
    """
    if threshold is None:
        threshold = Config.DEFAULT_DESKEW_THRESHOLD

    logger.info(f"开始图片纠偏检测（阈值: {threshold}°）")

    # 检测角度
    if use_simple:
        angle = detect_skew_angle_simple(image)
    else:
        angle = detect_skew_angle(image)

    # 判断是否需要纠正
    if abs(angle) < threshold:
        logger.info(f"倾斜角度 {angle:.2f}° 小于阈值 {threshold}°，跳过纠正")
        return image, angle

    # 纠正倾斜
    corrected = correct_skew(image, angle)

    return corrected, angle


def auto_rotate_by_text_orientation(image: np.ndarray) -> Tuple[np.ndarray, int]:
    """
    根据文字方向自动旋转图片（90/180/270度）

    用于处理扫描时方向错误的文档

    Args:
        image: 图片数组 (BGR格式)

    Returns:
        Tuple[np.ndarray, int]: (旋转后的图片, 旋转角度)
    """
    try:
        # 这个功能需要OCR引擎支持，暂时返回原图
        # TODO: 在Phase 3可以集成OCR方向检测
        logger.debug("文字方向检测（暂未实现）")
        return image, 0

    except Exception as e:
        logger.error(f"文字方向检测失败: {e}")
        return image, 0
