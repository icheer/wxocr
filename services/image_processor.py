"""
图片预处理服务

整合所有图像预处理功能，使用统一的预处理管道
"""
import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Tuple, Dict, Any
from utils.logger import get_logger
from services.image_preprocessor import (
    PreprocessingConfig,
    preprocess_image as pipeline_preprocess_image,
    preprocess_image_from_file
)

logger = get_logger(__name__)


class ImagePreprocessor:
    """图片预处理器（使用统一的预处理管道）"""

    def __init__(self,
                 remove_watermark: bool = False,
                 watermark_color: Optional[str] = None,
                 watermark_tolerance: int = 40,
                 deskew: bool = False,
                 denoise: bool = False,
                 denoise_method: str = 'median',
                 enhance_contrast: bool = False,
                 contrast_method: str = 'clahe',
                 binarize: bool = False,
                 binarize_method: str = 'gaussian',
                 sharpen: bool = False,
                 sharpen_strength: float = 1.0):
        """
        初始化预处理器

        Args:
            remove_watermark: 是否去除水印
            watermark_color: 水印颜色 (格式: "#RRGGBB")
            watermark_tolerance: 颜色容差
            deskew: 是否纠偏
            denoise: 是否去噪
            denoise_method: 去噪方法 ('median', 'fastNlMeans', 'bilateral')
            enhance_contrast: 是否增强对比度
            contrast_method: 对比度增强方法 ('clahe', 'histogram')
            binarize: 是否二值化
            binarize_method: 二值化方法 ('gaussian', 'otsu')
            sharpen: 是否锐化
            sharpen_strength: 锐化强度 (0.5 - 2.0)
        """
        # 创建配置对象
        self.config = PreprocessingConfig()
        self.config.remove_watermark = remove_watermark
        self.config.watermark_color = watermark_color
        self.config.watermark_tolerance = watermark_tolerance
        self.config.deskew = deskew
        self.config.denoise = denoise
        self.config.denoise_method = denoise_method
        self.config.enhance_contrast = enhance_contrast
        self.config.contrast_method = contrast_method
        self.config.binarize = binarize
        self.config.binarize_method = binarize_method
        self.config.sharpen = sharpen
        self.config.sharpen_strength = sharpen_strength

        self.last_result = None

    def process(self, image_path: str, output_path: Optional[str] = None) -> str:
        """
        处理图片

        Args:
            image_path: 输入图片路径
            output_path: 输出图片路径（可选）

        Returns:
            str: 输出图片路径
        """
        logger.info(f"开始预处理图片: {image_path}")

        # 使用统一的预处理管道
        processed_image, output_file = preprocess_image_from_file(
            image_path,
            self.config,
            output_path
        )

        # 保存结果（用于获取统计信息）
        self.last_result = processed_image

        return output_file

    def get_stats(self) -> Dict[str, Any]:
        """
        获取处理统计信息

        Returns:
            dict: 统计信息，包含应用的操作列表
        """
        if self.last_result is None:
            return {}

        # 从配置生成统计信息
        stats = {
            'watermark_removed': self.config.remove_watermark,
            'deskewed': self.config.deskew,
            'denoised': self.config.denoise,
            'contrast_enhanced': self.config.enhance_contrast,
            'binarized': self.config.binarize,
            'sharpened': self.config.sharpen and not self.config.binarize,
        }

        return stats


def preprocess_image(image_path: str,
                    output_path: Optional[str] = None,
                    remove_watermark: bool = False,
                    watermark_color: Optional[str] = None,
                    watermark_tolerance: int = 40,
                    deskew: bool = False,
                    denoise: bool = False,
                    denoise_method: str = 'median',
                    enhance_contrast: bool = False,
                    contrast_method: str = 'clahe',
                    binarize: bool = False,
                    binarize_method: str = 'gaussian',
                    sharpen: bool = False,
                    sharpen_strength: float = 1.0) -> Tuple[str, dict]:
    """
    预处理图片（函数式接口）

    Args:
        image_path: 输入图片路径
        output_path: 输出图片路径（可选）
        remove_watermark: 是否去除水印
        watermark_color: 水印颜色 (格式: "#RRGGBB")
        watermark_tolerance: 颜色容差
        deskew: 是否纠偏
        denoise: 是否去噪
        denoise_method: 去噪方法
        enhance_contrast: 是否增强对比度
        contrast_method: 对比度方法
        binarize: 是否二值化
        binarize_method: 二值化方法
        sharpen: 是否锐化
        sharpen_strength: 锐化强度

    Returns:
        Tuple[str, dict]: (输出路径, 统计信息)
    """
    preprocessor = ImagePreprocessor(
        remove_watermark=remove_watermark,
        watermark_color=watermark_color,
        watermark_tolerance=watermark_tolerance,
        deskew=deskew,
        denoise=denoise,
        denoise_method=denoise_method,
        enhance_contrast=enhance_contrast,
        contrast_method=contrast_method,
        binarize=binarize,
        binarize_method=binarize_method,
        sharpen=sharpen,
        sharpen_strength=sharpen_strength
    )

    output = preprocessor.process(image_path, output_path)
    stats = preprocessor.get_stats()

    return output, stats
