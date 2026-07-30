"""
PDF处理服务

提供PDF文档的智能处理，包括：
- 文本提取（纯文本PDF）
- 页面结构分析
- 图片提取
- 整页渲染
"""
import fitz  # PyMuPDF
from pathlib import Path
from typing import List, Dict, Tuple, Optional
from utils.logger import get_logger
from config.settings import Config

logger = get_logger(__name__)


class PdfProcessResult:
    """PDF处理结果"""
    def __init__(self):
        self.strategy = None  # 'text_extraction' | 'full_page_render' | 'extract_images' | 'mixed'
        self.text = ""  # 提取到的文本
        self.images = []  # 需要OCR的图片路径列表
        self.page_count = 0
        self.metadata = {}


def extract_text_from_page(page: fitz.Page) -> str:
    """
    从页面提取文本

    Args:
        page: PyMuPDF页面对象

    Returns:
        str: 提取到的文本
    """
    try:
        text = page.get_text().strip()
        return text
    except Exception as e:
        logger.error(f"提取页面文本失败: {e}")
        return ""


def analyze_page_structure(page: fitz.Page) -> Dict:
    """
    分析页面结构，决定处理策略

    Args:
        page: PyMuPDF页面对象

    Returns:
        dict: {
            'strategy': str,  # 处理策略
            'text': str,      # 提取到的文本
            'text_length': int,
            'image_count': int,
            'image_coverage': float,  # 图片覆盖率 0.0-1.0
            'has_large_image': bool   # 是否有大图（>80%）
        }
    """
    # 第一步：提取文本
    text = extract_text_from_page(page)
    text_length = len(text)

    # 第二步：分析图片
    page_rect = page.rect
    page_area = page_rect.width * page_rect.height

    images = page.get_images(full=True)
    image_count = len(images)
    total_image_coverage = 0.0
    has_large_image = False

    for img in images:
        try:
            xref = img[0]
            rects = page.get_image_rects(xref)
            if rects:
                for img_rect in rects:
                    coverage = (img_rect.width * img_rect.height) / page_area
                    total_image_coverage += coverage
                    if coverage > Config.MIN_IMAGE_COVERAGE_FULL_PAGE:
                        has_large_image = True
        except Exception as e:
            logger.warning(f"分析图片时出错: {e}")
            continue

    # 限制覆盖率在合理范围内（可能有重叠）
    total_image_coverage = min(total_image_coverage, 1.0)

    # 第三步：决策处理策略
    strategy = _determine_strategy(
        text_length=text_length,
        image_count=image_count,
        image_coverage=total_image_coverage,
        has_large_image=has_large_image
    )

    return {
        'strategy': strategy,
        'text': text,
        'text_length': text_length,
        'image_count': image_count,
        'image_coverage': total_image_coverage,
        'has_large_image': has_large_image
    }


def _determine_strategy(text_length: int, image_count: int,
                       image_coverage: float, has_large_image: bool) -> str:
    """
    根据页面特征决定处理策略

    优先级：
    1. 有效文本且图片覆盖率低 → text_extraction
    2. 单张大图且无文本 → full_page_render
    3. 有文本+有图片 → mixed
    4. 其他 → extract_images
    """
    # 策略1: 纯文本PDF（有效文本 + 图片覆盖率低）
    if text_length >= Config.MIN_TEXT_LENGTH_FOR_EXTRACTION and \
       image_coverage < Config.MAX_IMAGE_COVERAGE_FOR_TEXT:
        return 'text_extraction'

    # 策略2: 纯扫描页（单张大图 + 无文本）
    if has_large_image and image_count == 1 and \
       text_length < Config.MIN_TEXT_LENGTH_FOR_EXTRACTION:
        return 'full_page_render'

    # 策略3: 混合内容（有文本 + 有图片）
    if text_length >= Config.MIN_TEXT_LENGTH_FOR_EXTRACTION and \
       image_coverage >= Config.MAX_IMAGE_COVERAGE_FOR_TEXT:
        return 'mixed'

    # 策略4: 默认提取图片
    return 'extract_images' if image_count > 0 else 'full_page_render'


def render_full_page(page: fitz.Page, output_path: str, scale: float = None) -> str:
    """
    将整页渲染为图片

    Args:
        page: PyMuPDF页面对象
        output_path: 输出图片路径
        scale: 渲染缩放倍数（默认从配置读取）

    Returns:
        str: 输出图片路径
    """
    if scale is None:
        scale = Config.PDF_RENDER_SCALE

    try:
        # 创建缩放矩阵
        mat = fitz.Matrix(scale, scale)

        # 渲染页面
        pix = page.get_pixmap(matrix=mat, alpha=False)

        # 保存为PNG
        pix.save(output_path)

        logger.debug(f"页面渲染完成: {output_path}, 尺寸: {pix.width}x{pix.height}")
        return output_path

    except Exception as e:
        logger.error(f"页面渲染失败: {e}")
        raise


def extract_images_from_page(page: fitz.Page, doc: fitz.Document,
                             output_dir: Path, page_num: int) -> List[str]:
    """
    从页面提取内嵌图片

    Args:
        page: PyMuPDF页面对象
        doc: PyMuPDF文档对象
        output_dir: 输出目录
        page_num: 页码（用于命名）

    Returns:
        List[str]: 提取的图片路径列表
    """
    extracted_images = []
    images = page.get_images(full=True)

    for img_index, img in enumerate(images):
        try:
            xref = img[0]

            # 提取图片
            base_image = doc.extract_image(xref)
            image_bytes = base_image["image"]
            image_ext = base_image["ext"]

            # 生成文件名
            image_filename = f"page{page_num}_img{img_index}.{image_ext}"
            image_path = output_dir / image_filename

            # 保存图片
            with open(image_path, "wb") as img_file:
                img_file.write(image_bytes)

            extracted_images.append(str(image_path))
            logger.debug(f"提取图片: {image_path}")

        except Exception as e:
            logger.warning(f"提取图片 {img_index} 失败: {e}")
            continue

    return extracted_images


def process_pdf(pdf_path: str, output_dir: str = None) -> PdfProcessResult:
    """
    处理PDF文件

    Args:
        pdf_path: PDF文件路径
        output_dir: 输出目录（用于保存提取的图片）

    Returns:
        PdfProcessResult: 处理结果
    """
    result = PdfProcessResult()

    # 设置输出目录
    if output_dir is None:
        output_dir = Config.TEMP_DIR
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        # 打开PDF
        doc = fitz.open(pdf_path)
        result.page_count = len(doc)

        logger.info(f"开始处理PDF: {pdf_path}, 页数: {result.page_count}")

        # 检查页数限制
        if result.page_count > Config.MAX_PDF_PAGES:
            logger.warning(f"PDF页数 ({result.page_count}) 超过限制 ({Config.MAX_PDF_PAGES})")
            raise ValueError(f"PDF页数超过限制 ({Config.MAX_PDF_PAGES}页)")

        all_text_parts = []
        all_images = []
        strategies = []

        # 逐页处理
        for page_num in range(result.page_count):
            page = doc.load_page(page_num)
            logger.debug(f"处理第 {page_num + 1}/{result.page_count} 页")

            # 分析页面结构
            page_analysis = analyze_page_structure(page)
            strategy = page_analysis['strategy']
            strategies.append(strategy)

            logger.info(f"第{page_num + 1}页策略: {strategy}, "
                       f"文本长度: {page_analysis['text_length']}, "
                       f"图片数: {page_analysis['image_count']}, "
                       f"覆盖率: {page_analysis['image_coverage']:.2%}")

            # 根据策略处理
            if strategy == 'text_extraction':
                # 直接使用提取的文本
                all_text_parts.append(page_analysis['text'])

            elif strategy == 'full_page_render':
                # 整页渲染
                render_path = output_dir / f"page{page_num + 1}_full.png"
                render_full_page(page, str(render_path))
                all_images.append(str(render_path))

            elif strategy == 'extract_images':
                # 提取图片对象
                images = extract_images_from_page(page, doc, output_dir, page_num + 1)
                all_images.extend(images)

            elif strategy == 'mixed':
                # 混合模式：文本 + 图片OCR
                all_text_parts.append(page_analysis['text'])
                images = extract_images_from_page(page, doc, output_dir, page_num + 1)
                all_images.extend(images)

        # 确定最终策略（基于所有页面的主要策略）
        if all_images and all_text_parts:
            result.strategy = 'mixed'
        elif all_text_parts and not all_images:
            result.strategy = 'text_extraction'
        elif all_images:
            # 判断是整页渲染还是图片提取
            if 'full_page_render' in strategies:
                result.strategy = 'full_page_render'
            else:
                result.strategy = 'extract_images'
        else:
            result.strategy = 'text_extraction'

        result.text = '\n\n'.join(all_text_parts) if all_text_parts else ""
        result.images = all_images

        result.metadata = {
            'strategies_per_page': strategies,
            'text_pages': sum(1 for s in strategies if s in ('text_extraction', 'mixed')),
            'image_pages': sum(1 for s in strategies if s in ('full_page_render', 'extract_images', 'mixed')),
        }

        logger.info(f"PDF处理完成: 策略={result.strategy}, "
                   f"文本长度={len(result.text)}, "
                   f"图片数={len(result.images)}")

        doc.close()
        return result

    except Exception as e:
        logger.error(f"PDF处理失败: {e}")
        raise


def get_pdf_info(pdf_path: str) -> Dict:
    """
    获取PDF基本信息（不处理内容）

    Args:
        pdf_path: PDF文件路径

    Returns:
        dict: PDF信息
    """
    try:
        doc = fitz.open(pdf_path)
        info = {
            'page_count': len(doc),
            'metadata': doc.metadata,
            'is_encrypted': doc.is_encrypted,
        }
        doc.close()
        return info
    except Exception as e:
        logger.error(f"获取PDF信息失败: {e}")
        return {'error': str(e)}
