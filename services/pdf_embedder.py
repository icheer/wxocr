"""
PDF 文本嵌入服务

将 OCR 识别的文本块嵌入到图片或 PDF 中，生成可搜索的 PDF
使用 PyMuPDF (fitz) 实现，支持中文
"""
import fitz  # PyMuPDF
import re
from PIL import Image
from pathlib import Path
from utils.logger import get_logger

logger = get_logger(__name__)


def _is_chinese_char(char):
    """判断字符是否为中文字符（包括中文标点符号）"""
    code = ord(char)
    # CJK统一汉字: 4E00-9FFF
    # CJK扩展A: 3400-4DBF
    # CJK扩展B: 20000-2A6DF
    # CJK标点符号: 3000-303F
    # 全角ASCII、全角中英文标点: FF00-FFEF
    return (0x4E00 <= code <= 0x9FFF or      # 基本汉字
            0x3400 <= code <= 0x4DBF or      # 扩展A
            0x20000 <= code <= 0x2A6DF or    # 扩展B
            0x3000 <= code <= 0x303F or      # CJK符号和标点
            0xFF00 <= code <= 0xFFEF)        # 全角ASCII和标点


def _embed_text_with_mixed_fonts(page, text, left, bottom, fontsize):
    """
    使用混合字体嵌入文本（中文用china-s，非中文用helv）

    Args:
        page: PyMuPDF页面对象
        text: 要嵌入的文本
        left: 起始x坐标
        bottom: 基线y坐标
        fontsize: 字体大小

    Returns:
        bool: 是否成功
    """
    try:
        # 智能分段处理
        segments = _split_text_by_language(text)

        # 基线位置：左下角
        current_x = left

        for segment_text, is_chinese in segments:
            if not segment_text:
                continue

            # 选择字体
            fontname = "china-s" if is_chinese else "helv"

            point = fitz.Point(current_x, bottom)

            # 插入文本段
            page.insert_text(
                point,
                segment_text,
                fontsize=fontsize,
                fontname=fontname,
                color=(1, 1, 1),
                render_mode=3,
                overlay=True
            )

            # 估算文本宽度，更新 x 坐标
            if is_chinese:
                char_width = fontsize
            else:
                char_width = fontsize * 0.6

            current_x += len(segment_text) * char_width

        return True

    except Exception as e:
        logger.warning(f"嵌入文本失败: {text[:20]}..., 错误: {e}")
        return False
    """
    将文本按中文和非中文分段

    Returns:
        list of (text_segment, is_chinese)
    """
    if not text:
        return []

    segments = []
    current_segment = ""
    current_is_chinese = None

    for char in text:
        is_chinese = _is_chinese_char(char)

        if current_is_chinese is None:
            # 第一个字符
            current_segment = char
            current_is_chinese = is_chinese
        elif is_chinese == current_is_chinese:
            # 同类型字符，追加
            current_segment += char
        else:
            # 类型变化，保存当前段落，开始新段落
            if current_segment:
                segments.append((current_segment, current_is_chinese))
            current_segment = char
            current_is_chinese = is_chinese

    # 保存最后一个段落
    if current_segment:
        segments.append((current_segment, current_is_chinese))

    return segments


def embed_text_to_image(image_path: str, ocr_response: list, output_pdf_path: str):
    """
    将文本块嵌入到图片中，生成 PDF

    Args:
        image_path: 原始图片路径
        ocr_response: OCR 识别结果列表，每项包含 text, left, top, right, bottom
        output_pdf_path: 输出 PDF 路径
    """
    logger.info(f"[embed_text_to_image] 开始处理")
    logger.info(f"[embed_text_to_image] 图片路径: {image_path}")
    logger.info(f"[embed_text_to_image] 输出路径: {output_pdf_path}")
    logger.info(f"[embed_text_to_image] 文本块数量: {len(ocr_response)}")

    try:
        # 打开图片获取尺寸
        img = Image.open(image_path)
        img_width, img_height = img.size
        logger.info(f"[embed_text_to_image] 图片尺寸: {img_width}x{img_height}")

        # 创建 PDF 文档
        doc = fitz.open()
        logger.info(f"[embed_text_to_image] PDF 文档已创建")

        # 创建页面
        page = doc.new_page(width=img_width, height=img_height)
        logger.info(f"[embed_text_to_image] 页面已创建")

        # 插入图片作为背景
        page.insert_image(fitz.Rect(0, 0, img_width, img_height), filename=image_path)
        logger.info(f"[embed_text_to_image] 背景图片已插入")

        # 获取可用字体列表
        try:
            available_fonts = fitz.fitz_fontdescriptors.keys()
            logger.info(f"[embed_text_to_image] 可用字体: {list(available_fonts)[:10]}")
        except Exception as font_list_error:
            logger.warning(f"[embed_text_to_image] 无法获取字体列表: {font_list_error}")

        # 尝试不同的字体名称
        font_names = ["china-s", "cjk", "noto", "helv"]
        selected_font = "helv"  # 默认字体

        for font_name in font_names:
            try:
                # 测试字体是否可用
                test_rect = fitz.Rect(0, 0, 100, 20)
                test_rc = page.insert_textbox(
                    test_rect,
                    "测试",
                    fontsize=10,
                    fontname=font_name,
                    color=(1, 1, 1),
                    overlay=False
                )
                if test_rc >= 0:
                    selected_font = font_name
                    logger.info(f"[embed_text_to_image] 选择字体: {font_name}")
                    break
            except Exception as font_error:
                logger.debug(f"[embed_text_to_image] 字体 {font_name} 不可用: {font_error}")
                continue

        # 清除测试文本
        doc.close()
        doc = fitz.open()
        page = doc.new_page(width=img_width, height=img_height)
        page.insert_image(fitz.Rect(0, 0, img_width, img_height), filename=image_path)

        logger.info(f"[embed_text_to_image] 开始嵌入 {len(ocr_response)} 个文本块，使用字体: {selected_font}")

        # 嵌入文本块
        embedded_count = 0
        for i, block in enumerate(ocr_response):
            text = block.get('text', '').strip()
            if not text:
                logger.debug(f"[embed_text_to_image] 文本块 {i} 为空，跳过")
                continue

            # 获取坐标
            left = float(block.get('left', 0))
            top = float(block.get('top', 0))
            right = float(block.get('right', 0))
            bottom = float(block.get('bottom', 0))

            width = right - left
            height = bottom - top

            if width <= 0 or height <= 0:
                logger.debug(f"[embed_text_to_image] 文本块 {i} 尺寸无效: {width}x{height}")
                continue

            # 计算合适的字体大小
            # 根据文本块的高度和宽度来估算字体大小
            fontsize = height * 0.9  # 使用较大的比例

            # 确保字体大小合理
            if fontsize < 4:
                fontsize = 4
            elif fontsize > 100:
                fontsize = 100

            try:
                # 使用复用的混合字体嵌入函数
                success = _embed_text_with_mixed_fonts(page, text, left, bottom, fontsize)

                if success:
                    embedded_count += 1
                    logger.debug(f"[embed_text_to_image] 文本块 {i} 嵌入成功: {text[:20]}, 位置: ({left}, {bottom}), 字体: {fontsize:.1f}")
                else:
                    logger.warning(f"[embed_text_to_image] 文本块 {i} 嵌入失败: {text[:20]}")

            except Exception as e:
                logger.warning(f"[embed_text_to_image] 文本块 {i} 嵌入异常: {text[:20]}, 错误: {e}")
                continue

        logger.info(f"[embed_text_to_image] 成功嵌入 {embedded_count}/{len(ocr_response)} 个文本块")

        # 保存 PDF
        doc.save(output_pdf_path, garbage=4, deflate=True)
        doc.close()

        logger.info(f"[embed_text_to_image] PDF 已保存到: {output_pdf_path}")
        logger.info(f"[embed_text_to_image] 处理完成")

    except Exception as e:
        logger.error(f"[embed_text_to_image] 处理失败: {e}", exc_info=True)
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

        total_embedded = 0

        # 为每一页嵌入文本
        for page_data in pages_data:
            page_num = page_data.get('page_number', 1)
            page_index = page_num - 1

            if page_index >= doc.page_count:
                logger.warning(f"页码 {page_num} 超出范围，跳过")
                continue

            # 获取页面
            page = doc[page_index]

            # 获取 OCR 返回的页面尺寸（可能是放大后的）
            ocr_width = float(page_data.get('width', 0))
            ocr_height = float(page_data.get('height', 0))

            # 获取实际 PDF 页面尺寸
            page_rect = page.rect
            actual_width = page_rect.width
            actual_height = page_rect.height

            # 计算缩放比例
            scale_x = actual_width / ocr_width if ocr_width > 0 else 1.0
            scale_y = actual_height / ocr_height if ocr_height > 0 else 1.0

            logger.info(f"页码 {page_num} 尺寸: OCR({ocr_width}x{ocr_height}), 实际({actual_width}x{actual_height}), 缩放({scale_x:.3f}, {scale_y:.3f})")

            ocr_response = page_data.get('ocr_response', [])

            if not ocr_response:
                # 没有文本块，跳过
                logger.debug(f"页码 {page_num} 没有文本块，跳过")
                continue

            embedded_count = 0

            # 嵌入不可见文本块
            for block in ocr_response:
                text = block.get('text', '').strip()
                if not text:
                    continue

                # 获取 OCR 坐标（放大后的）
                left = float(block.get('left', 0))
                top = float(block.get('top', 0))
                right = float(block.get('right', 0))
                bottom = float(block.get('bottom', 0))

                # 缩放到实际 PDF 坐标
                left = left * scale_x
                top = top * scale_y
                right = right * scale_x
                bottom = bottom * scale_y

                block_width = right - left
                block_height = bottom - top

                if block_width <= 0 or block_height <= 0:
                    continue

                # 计算字体大小
                fontsize = block_height * 0.9

                # 确保字体大小合理
                if fontsize < 4:
                    fontsize = 4
                elif fontsize > 100:
                    fontsize = 100

                try:
                    # 使用复用的混合字体嵌入函数
                    success = _embed_text_with_mixed_fonts(page, text, left, bottom, fontsize)

                    if success:
                        embedded_count += 1
                        total_embedded += 1

                except Exception as e:
                    logger.warning(f"页码 {page_num} 嵌入文本块失败: {text[:20]}..., 错误: {e}")
                    continue

            logger.info(f"页码 {page_num} 成功嵌入 {embedded_count}/{len(ocr_response)} 个文本块")

        logger.info(f"PDF 总共成功嵌入 {total_embedded} 个文本块")

        # 保存 PDF
        doc.save(output_pdf_path, garbage=4, deflate=True)
        doc.close()

        logger.info(f"PDF 嵌入文本完成，输出: {output_pdf_path}")

    except Exception as e:
        logger.error(f"PDF 嵌入文本失败: {e}", exc_info=True)
        raise
