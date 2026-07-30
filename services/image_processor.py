"""
图片预处理服务

整合水印去除和图片纠偏功能
"""
import cv2
import numpy as np
from pathlib import Path
from typing import Optional, Tuple
from utils.logger import get_logger
from utils.watermark_remover import remove_watermark
from utils.deskew_helper import deskew_image

logger = get_logger(__name__)


class ImagePreprocessor:
    """图片预处理器"""

    def __init__(self, remove_watermark_enabled: bool = False,
                 watermark_color: Optional[Tuple[int, int, int]] = None,
                 watermark_tolerance: int = 40,
                 deskew_enabled: bool = False):
        """
        初始化预处理器

        Args:
            remove_watermark_enabled: 是否启用水印去除
            watermark_color: 水印颜色 (R, G, B)
            watermark_tolerance: 颜色容差
            deskew_enabled: 是否启用纠偏
        """
        self.remove_watermark_enabled = remove_watermark_enabled
        self.watermark_color = watermark_color
        self.watermark_tolerance = watermark_tolerance
        self.deskew_enabled = deskew_enabled

        self.stats = {
            'watermark_removed': False,
            'deskewed': False,
            'skew_angle': 0.0
        }

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

        # 读取图片
        image = cv2.imread(image_path)
        if image is None:
            raise ValueError(f"无法读取图片: {image_path}")

        original_shape = image.shape
        logger.debug(f"原始图片尺寸: {original_shape}")

        # 步骤1: 去除水印
        if self.remove_watermark_enabled:
            logger.info("执行水印去除...")
            image = remove_watermark(
                image,
                watermark_color=self.watermark_color,
                tolerance=self.watermark_tolerance,
                use_inpainting=False  # 不使用修复算法，速度优先
            )
            self.stats['watermark_removed'] = True

        # 步骤2: 图片纠偏
        if self.deskew_enabled:
            logger.info("执行图片纠偏...")
            image, angle = deskew_image(image)
            self.stats['deskewed'] = abs(angle) > 0.1
            self.stats['skew_angle'] = angle

        # 保存结果
        if output_path is None:
            # 覆盖原文件
            output_path = image_path

        cv2.imwrite(output_path, image)
        logger.info(f"预处理完成: {output_path}")

        return output_path

    def get_stats(self) -> dict:
        """获取处理统计信息"""
        return self.stats.copy()


def preprocess_image(image_path: str,
                    output_path: Optional[str] = None,
                    remove_watermark: bool = False,
                    watermark_color: Optional[Tuple[int, int, int]] = None,
                    watermark_tolerance: int = 40,
                    deskew: bool = False) -> Tuple[str, dict]:
    """
    预处理图片（函数式接口）

    Args:
        image_path: 输入图片路径
        output_path: 输出图片路径（可选）
        remove_watermark: 是否去除水印
        watermark_color: 水印颜色 (R, G, B)
        watermark_tolerance: 颜色容差
        deskew: 是否纠偏

    Returns:
        Tuple[str, dict]: (输出路径, 统计信息)
    """
    preprocessor = ImagePreprocessor(
        remove_watermark_enabled=remove_watermark,
        watermark_color=watermark_color,
        watermark_tolerance=watermark_tolerance,
        deskew_enabled=deskew
    )

    output = preprocessor.process(image_path, output_path)
    stats = preprocessor.get_stats()

    return output, stats
