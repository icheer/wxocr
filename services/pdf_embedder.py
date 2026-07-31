"""
PDF 文本嵌入服务

将 OCR 识别的文本块嵌入到图片或 PDF 中，生成可搜索的 PDF
使用 PyMuPDF (fitz) 实现，支持中文
"""
import fitz  # PyMuPDF
from PIL import Image
from pathlib import Path
from utils.logger import get_logger

logger = get_logger(__name__)


def embed_text_to_image(image_path: str, ocr_response: list, output_pdf_path: str):
    """
    将文本块嵌入到图片中，生成 PDF

    Args:
        image_path: 原始图片路径
        ocr_response: OCR 识别结果列表，每项包含 text, left, top, right, bottom
        output_pdf_path: 输出 PDF 路径
    """
    try:
        # 打开图片获取尺寸
        img = Image.open(image_path)
        img_width, img_height = img.size

        logger.info(f"图片尺寸: {img_width}x{img_height}, 文本块数量: {len(ocr_response)}")

        # 创建 PDF 文档
        doc = fitz.open()

        # 创建页面
        page = doc.new_page(width=img_width, height=img_height)

        # 插入图片作为背景
        page.insert_image(fitz.Rect(0, 0, img_width, img_height), filename=image_path)

        # 嵌入不可见文本块
        for block in ocr_response:
            text = block.get('text', '').strip()
            if not text:
                continue

            # 获取坐标（OCR 返回的是图片坐标系）
            left = float(block.get('left', 0))
            top = float(block.get('top', 0))
            right = float(block.get('right', 0))
            bottom = float(block.get('bottom', 0))

            # 计算宽高
            width = right - left
            height = bottom - top

            if width <= 0 or height <= 0:
                continue

            # PyMuPDF 坐标系：左上角为原点（与 OCR 一致）
            rect = fitz.Rect(left, top, right, bottom)

            # 计算合适的字体大小
            fontsize = height * 0.8
            if fontsize < 1:
                fontsize = 1

            # 插入不可见文本（白色文本，渲染模式为不可见）
            # 使用 insert_textbox 并设置 render_mode=3（不可见但可选择）
            page.insert_textbox(
                rect,
                text,
                fontsize=fontsize,
                fontname="china-s",  # 使用内置中文字体（简体）
                color=(1, 1, 1),  # 白色（不可见）
                render_mode=3,  # 不可见模式
                align=fitz.TEXT_ALIGN_LEFT
            )

        # 保存 PDF
        doc.save(output_pdf_path)
        doc.close()

        logger.info(f"图片嵌入文本完成，输出: {output_pdf_path}")

    except Exception as e:
        logger.error(f"图片嵌入文本失败: {e}", exc_info=True)
        raise


def embed_text_to_pdf(pdf_path: str, pages_data: list, output_pdf_path: str):
    """
    将文本块嵌入到 PDF 的每一页中

    Args:
        pdf_path: 原始 PDF 路径
        pages_data: 页面数据列表，每项包含 page_number, width, height, ocr_response
        output_pdf_path: 输出 PDF 路径
    """
    try:
        # 打开原始 PDF
        doc = fitz.open(pdf_path)

        logger.info(f"PDF 页数: {doc.page_count}, 待嵌入页数: {len(pages_data)}")

        # 为每一页嵌入文本
        for page_data in pages_data:
            page_num = page_data.get('page_number', 1)
            page_index = page_num - 1

            if page_index >= doc.page_count:
                logger.warning(f"页码 {page_num} 超出范围，跳过")
                continue

            # 获取页面
            page = doc[page_index]

            # 获取页面尺寸
            width = float(page_data.get('width', 0))
            height = float(page_data.get('height', 0))

            if width <= 0 or height <= 0:
                # 使用页面实际尺寸
                rect = page.rect
                width = rect.width
                height = rect.height

            ocr_response = page_data.get('ocr_response', [])

            if not ocr_response:
                # 没有文本块，跳过
                continue

            # 嵌入不可见文本块
            for block in ocr_response:
                text = block.get('text', '').strip()
                if not text:
                    continue

                left = float(block.get('left', 0))
                top = float(block.get('top', 0))
                right = float(block.get('right', 0))
                bottom = float(block.get('bottom', 0))

                block_width = right - left
                block_height = bottom - top

                if block_width <= 0 or block_height <= 0:
                    continue

                # PyMuPDF 坐标系：左上角为原点
                rect = fitz.Rect(left, top, right, bottom)

                # 计算字体大小
                fontsize = block_height * 0.8
                if fontsize < 1:
                    fontsize = 1

                # 插入不可见文本
                page.insert_textbox(
                    rect,
                    text,
                    fontsize=fontsize,
                    fontname="china-s",  # 使用内置中文字体
                    color=(1, 1, 1),  # 白色（不可见）
                    render_mode=3,  # 不可见模式
                    align=fitz.TEXT_ALIGN_LEFT
                )

        # 保存 PDF
        doc.save(output_pdf_path)
        doc.close()

        logger.info(f"PDF 嵌入文本完成，输出: {output_pdf_path}")

    except Exception as e:
        logger.error(f"PDF 嵌入文本失败: {e}", exc_info=True)
        raise
