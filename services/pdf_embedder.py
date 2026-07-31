"""
PDF 文本嵌入服务

将 OCR 识别的文本块嵌入到图片或 PDF 中，生成可搜索的 PDF
"""
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from PyPDF2 import PdfReader, PdfWriter
from PIL import Image
from pathlib import Path
import io
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

        # 创建 PDF
        c = canvas.Canvas(output_pdf_path, pagesize=(img_width, img_height))

        # 绘制图片作为背景
        c.drawImage(image_path, 0, 0, width=img_width, height=img_height)

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

            # PDF 坐标系是左下角为原点，需要转换
            # 图片坐标系：左上角为原点，y 向下
            # PDF 坐标系：左下角为原点，y 向上
            pdf_x = left
            pdf_y = img_height - bottom

            # 设置文本渲染模式为不可见（模式 3）
            c.setFillColorRGB(1, 1, 1, alpha=0)  # 完全透明
            c.setStrokeColorRGB(1, 1, 1, alpha=0)

            # 计算字体大小（简单估算）
            font_size = height * 0.8
            if font_size < 1:
                font_size = 1

            c.setFont("Helvetica", font_size)

            # 绘制不可见文本
            text_obj = c.beginText(pdf_x, pdf_y)
            text_obj.setTextRenderMode(3)  # 不可见模式
            text_obj.textLine(text)
            c.drawText(text_obj)

        c.save()
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
        # 读取原始 PDF
        reader = PdfReader(pdf_path)
        writer = PdfWriter()

        logger.info(f"PDF 页数: {len(reader.pages)}, 待嵌入页数: {len(pages_data)}")

        # 为每一页嵌入文本
        for page_data in pages_data:
            page_num = page_data.get('page_number', 1)
            page_index = page_num - 1

            if page_index >= len(reader.pages):
                logger.warning(f"页码 {page_num} 超出范围，跳过")
                continue

            # 获取原始页面
            original_page = reader.pages[page_index]

            # 获取页面尺寸
            width = float(page_data.get('width', 0))
            height = float(page_data.get('height', 0))

            if width <= 0 or height <= 0:
                # 使用原始页面尺寸
                media_box = original_page.mediabox
                width = float(media_box.width)
                height = float(media_box.height)

            ocr_response = page_data.get('ocr_response', [])

            if not ocr_response:
                # 没有文本块，直接添加原页面
                writer.add_page(original_page)
                continue

            # 创建文本层
            packet = io.BytesIO()
            c = canvas.Canvas(packet, pagesize=(width, height))

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

                # 转换坐标系
                pdf_x = left
                pdf_y = height - bottom

                # 设置不可见文本
                c.setFillColorRGB(1, 1, 1, alpha=0)
                c.setStrokeColorRGB(1, 1, 1, alpha=0)

                font_size = block_height * 0.8
                if font_size < 1:
                    font_size = 1

                c.setFont("Helvetica", font_size)

                text_obj = c.beginText(pdf_x, pdf_y)
                text_obj.setTextRenderMode(3)
                text_obj.textLine(text)
                c.drawText(text_obj)

            c.save()

            # 合并文本层和原始页面
            packet.seek(0)
            text_layer = PdfReader(packet)
            text_page = text_layer.pages[0]

            # 将文本层叠加到原始页面
            original_page.merge_page(text_page)
            writer.add_page(original_page)

        # 写入输出文件
        with open(output_pdf_path, 'wb') as output_file:
            writer.write(output_file)

        logger.info(f"PDF 嵌入文本完成，输出: {output_pdf_path}")

    except Exception as e:
        logger.error(f"PDF 嵌入文本失败: {e}", exc_info=True)
        raise
