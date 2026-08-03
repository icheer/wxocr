"""
图像预处理管道

统一的图像预处理工作流，支持多种预处理操作的组合
适用于单张图片和 PDF 页面的处理
"""
import cv2
import numpy as np
from pathlib import Path
from typing import Dict, Optional, Tuple
from utils.logger import get_logger
from utils.watermark_remover import remove_watermark
from utils.deskew_helper import deskew_image
from config.settings import Config

logger = get_logger(__name__)


class PreprocessingConfig:
    """预处理配置类"""
    def __init__(self):
        # 水印去除
        self.remove_watermark = False
        self.watermark_color = None  # 格式: "#RRGGBB"
        self.watermark_tolerance = Config.DEFAULT_WATERMARK_TOLERANCE

        # 自动纠偏
        self.deskew = False
        self.deskew_threshold = Config.DEFAULT_DESKEW_THRESHOLD

        # 去噪
        self.denoise = False
        self.denoise_method = 'median'  # 'median', 'fastNlMeans', 'bilateral'

        # 对比度增强
        self.enhance_contrast = False
        self.contrast_method = 'clahe'  # 'clahe', 'histogram'

        # 二值化
        self.binarize = False
        self.binarize_method = 'gaussian'  # 'gaussian', 'otsu'

        # 锐化
        self.sharpen = False
        self.sharpen_strength = 1.0

    def to_dict(self):
        """转换为字典"""
        return {
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
        }

    def has_any_preprocessing(self):
        """是否启用了任何预处理"""
        return (self.remove_watermark or self.deskew or self.denoise or
                self.enhance_contrast or self.binarize or self.sharpen)


class PreprocessingResult:
    """预处理结果"""
    def __init__(self):
        self.image = None  # 处理后的图像（numpy array）
        self.applied_operations = []  # 已应用的操作列表
        self.skipped_operations = []  # 跳过的操作列表
        self.warnings = []  # 警告信息


def denoise_image(image: np.ndarray, method: str = 'median') -> np.ndarray:
    """
    去噪处理

    Args:
        image: 输入图像
        method: 去噪方法
            - 'median': 中值滤波（快速，适合椒盐噪声）
            - 'fastNlMeans': 非局部均值去噪（效果好但慢）
            - 'bilateral': 双边滤波（保留边缘）

    Returns:
        去噪后的图像
    """
    try:
        if method == 'median':
            # 中值滤波 - 快速去除椒盐噪声
            denoised = cv2.medianBlur(image, 3)
            logger.debug("应用中值滤波去噪")

        elif method == 'fastNlMeans':
            # 非局部均值去噪 - 效果好但较慢
            if len(image.shape) == 3:
                denoised = cv2.fastNlMeansDenoisingColored(image, None, 10, 10, 7, 21)
            else:
                denoised = cv2.fastNlMeansDenoising(image, None, 10, 7, 21)
            logger.debug("应用非局部均值去噪")

        elif method == 'bilateral':
            # 双边滤波 - 保留边缘的同时去噪
            denoised = cv2.bilateralFilter(image, 9, 75, 75)
            logger.debug("应用双边滤波去噪")

        else:
            logger.warning(f"未知的去噪方法: {method}，使用中值滤波")
            denoised = cv2.medianBlur(image, 3)

        return denoised

    except Exception as e:
        logger.error(f"去噪处理失败: {e}")
        return image


def enhance_contrast(image: np.ndarray, method: str = 'clahe') -> np.ndarray:
    """
    对比度增强

    Args:
        image: 输入图像
        method: 增强方法
            - 'clahe': 自适应直方图均衡化（推荐）
            - 'histogram': 标准直方图均衡化

    Returns:
        增强后的图像
    """
    try:
        # 转换为灰度图
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            is_color = True
        else:
            gray = image.copy()
            is_color = False

        if method == 'clahe':
            # CLAHE - 自适应直方图均衡化
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)
            logger.debug("应用 CLAHE 对比度增强")

        elif method == 'histogram':
            # 标准直方图均衡化
            enhanced = cv2.equalizeHist(gray)
            logger.debug("应用直方图均衡化")

        else:
            logger.warning(f"未知的对比度增强方法: {method}，使用 CLAHE")
            clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
            enhanced = clahe.apply(gray)

        # 如果原图是彩色，转回彩色
        if is_color:
            enhanced = cv2.cvtColor(enhanced, cv2.COLOR_GRAY2BGR)

        return enhanced

    except Exception as e:
        logger.error(f"对比度增强失败: {e}")
        return image


def binarize_image(image: np.ndarray, method: str = 'gaussian') -> np.ndarray:
    """
    图像二值化

    Args:
        image: 输入图像
        method: 二值化方法
            - 'gaussian': 自适应高斯阈值（推荐）
            - 'otsu': Otsu 自动阈值

    Returns:
        二值化后的图像
    """
    try:
        # 转换为灰度图
        if len(image.shape) == 3:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        else:
            gray = image.copy()

        if method == 'gaussian':
            # 自适应高斯阈值
            binary = cv2.adaptiveThreshold(
                gray, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                blockSize=11, C=2
            )
            logger.debug("应用自适应高斯阈值二值化")

        elif method == 'otsu':
            # Otsu 自动阈值
            _, binary = cv2.threshold(
                gray, 0, 255,
                cv2.THRESH_BINARY + cv2.THRESH_OTSU
            )
            logger.debug("应用 Otsu 二值化")

        else:
            logger.warning(f"未知的二值化方法: {method}，使用自适应高斯阈值")
            binary = cv2.adaptiveThreshold(
                gray, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY,
                blockSize=11, C=2
            )

        # 转回 BGR 格式（保持一致性）
        binary_bgr = cv2.cvtColor(binary, cv2.COLOR_GRAY2BGR)
        return binary_bgr

    except Exception as e:
        logger.error(f"二值化处理失败: {e}")
        return image


def sharpen_image(image: np.ndarray, strength: float = 1.0) -> np.ndarray:
    """
    图像锐化

    Args:
        image: 输入图像
        strength: 锐化强度 (0.5 - 2.0)

    Returns:
        锐化后的图像
    """
    try:
        # 使用 Unsharp Mask 方法（更柔和）
        blurred = cv2.GaussianBlur(image, (0, 0), sigmaX=1.0)
        sharpened = cv2.addWeighted(image, 1.0 + strength, blurred, -strength, 0)
        logger.debug(f"应用锐化处理，强度: {strength}")
        return sharpened

    except Exception as e:
        logger.error(f"锐化处理失败: {e}")
        return image


def preprocess_image(image: np.ndarray, config: PreprocessingConfig) -> PreprocessingResult:
    """
    图像预处理主流程

    按照最优顺序执行预处理操作：
    1. 水印去除
    2. 自动纠偏
    3. 去噪
    4. 对比度增强
    5. 二值化
    6. 锐化（如果未二值化）

    Args:
        image: 输入图像（numpy array, BGR 格式）
        config: 预处理配置

    Returns:
        PreprocessingResult: 预处理结果
    """
    result = PreprocessingResult()
    result.image = image.copy()

    logger.info(f"开始图像预处理: {config.to_dict()}")

    # 1. 水印去除
    if config.remove_watermark:
        try:
            # 处理颜色格式：支持字符串 "#RRGGBB" 或元组 (R, G, B)
            watermark_rgb = None
            if config.watermark_color:
                if isinstance(config.watermark_color, str):
                    # 字符串格式：#RRGGBB -> (R, G, B)
                    color_hex = config.watermark_color.lstrip('#')
                    watermark_rgb = tuple(int(color_hex[i:i+2], 16) for i in (0, 2, 4))
                elif isinstance(config.watermark_color, (tuple, list)):
                    # 已经是元组/列表格式，直接使用
                    watermark_rgb = tuple(config.watermark_color)
                else:
                    logger.warning(f"不支持的水印颜色格式: {type(config.watermark_color)}")

            result.image = remove_watermark(
                result.image,
                watermark_color=watermark_rgb,
                tolerance=config.watermark_tolerance
            )
            result.applied_operations.append('watermark_removal')
            logger.info("✓ 水印去除完成")
        except Exception as e:
            logger.error(f"水印去除失败: {e}", exc_info=True)
            result.warnings.append(f"水印去除失败: {str(e)}")

    # 2. 自动纠偏
    if config.deskew:
        try:
            result.image, angle = deskew_image(
                result.image,
                threshold=config.deskew_threshold
            )
            if angle != 0:
                result.applied_operations.append(f'deskew (angle: {angle:.2f}°)')
                logger.info(f"✓ 自动纠偏完成，旋转角度: {angle:.2f}°")
            else:
                result.skipped_operations.append('deskew (angle < threshold)')
                logger.info("✓ 图像已正位，跳过纠偏")
        except Exception as e:
            logger.error(f"自动纠偏失败: {e}")
            result.warnings.append(f"自动纠偏失败: {str(e)}")

    # 3. 去噪
    if config.denoise:
        try:
            result.image = denoise_image(result.image, method=config.denoise_method)
            result.applied_operations.append(f'denoise ({config.denoise_method})')
            logger.info(f"✓ 去噪完成，方法: {config.denoise_method}")
        except Exception as e:
            logger.error(f"去噪失败: {e}")
            result.warnings.append(f"去噪失败: {str(e)}")

    # 4. 对比度增强
    if config.enhance_contrast:
        try:
            result.image = enhance_contrast(result.image, method=config.contrast_method)
            result.applied_operations.append(f'contrast_enhancement ({config.contrast_method})')
            logger.info(f"✓ 对比度增强完成，方法: {config.contrast_method}")
        except Exception as e:
            logger.error(f"对比度增强失败: {e}")
            result.warnings.append(f"对比度增强失败: {str(e)}")

    # 5. 二值化
    if config.binarize:
        try:
            result.image = binarize_image(result.image, method=config.binarize_method)
            result.applied_operations.append(f'binarization ({config.binarize_method})')
            logger.info(f"✓ 二值化完成，方法: {config.binarize_method}")

            # 二值化后跳过锐化
            if config.sharpen:
                result.skipped_operations.append('sharpen (binary image)')
                logger.info("✓ 已二值化，跳过锐化")
        except Exception as e:
            logger.error(f"二值化失败: {e}")
            result.warnings.append(f"二值化失败: {str(e)}")

    # 6. 锐化（仅在未二值化时执行）
    elif config.sharpen:
        try:
            result.image = sharpen_image(result.image, strength=config.sharpen_strength)
            result.applied_operations.append(f'sharpen (strength: {config.sharpen_strength})')
            logger.info(f"✓ 锐化完成，强度: {config.sharpen_strength}")
        except Exception as e:
            logger.error(f"锐化失败: {e}")
            result.warnings.append(f"锐化失败: {str(e)}")

    logger.info(f"图像预处理完成，应用操作: {result.applied_operations}")
    if result.warnings:
        logger.warning(f"预处理警告: {result.warnings}")

    return result


def preprocess_image_from_file(
    image_path: str,
    config: PreprocessingConfig,
    output_path: Optional[str] = None
) -> Tuple[np.ndarray, str]:
    """
    从文件读取图像并预处理

    Args:
        image_path: 输入图像路径
        config: 预处理配置
        output_path: 输出路径（可选，不提供则自动生成）

    Returns:
        (处理后的图像, 输出路径)
    """
    # 读取图像
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"无法读取图像: {image_path}")

    # 执行预处理
    result = preprocess_image(image, config)

    # 生成输出路径
    if output_path is None:
        input_path = Path(image_path)
        output_path = str(input_path.parent / f"{input_path.stem}_preprocessed{input_path.suffix}")

    # 保存图像
    cv2.imwrite(output_path, result.image)
    logger.info(f"预处理后的图像已保存: {output_path}")

    return result.image, output_path
