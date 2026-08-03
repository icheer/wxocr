"""
智能文本排版服务
将 OCR 识别结果智能排版为易读的文本格式
"""

import logging
from typing import List, Dict, Any, Tuple
from dataclasses import dataclass

logger = logging.getLogger(__name__)


@dataclass
class TextBlock:
    """文本块数据类"""
    text: str
    left: float
    top: float
    right: float
    bottom: float
    rate: float

    @property
    def center_y(self) -> float:
        """垂直中心点"""
        return (self.top + self.bottom) / 2

    @property
    def center_x(self) -> float:
        """水平中心点"""
        return (self.left + self.right) / 2

    @property
    def width(self) -> float:
        """宽度"""
        return self.right - self.left

    @property
    def height(self) -> float:
        """高度"""
        return self.bottom - self.top


@dataclass
class Row:
    """行数据类"""
    blocks: List[TextBlock]
    avg_top: float
    avg_bottom: float

    def sort_by_left(self):
        """按左边界排序"""
        self.blocks.sort(key=lambda b: b.left)


class TextFormatter:
    """文本智能排版器"""

    def __init__(self,
                 row_threshold_ratio: float = 0.5,
                 gap_threshold_ratio: float = 2.0,
                 paragraph_spacing_ratio: float = 1.5,
                 min_confidence: float = 0.3,
                 column_separator: str = "\t"):
        """
        初始化排版器

        Args:
            row_threshold_ratio: 行聚合阈值系数
            gap_threshold_ratio: 列间距判断系数
            paragraph_spacing_ratio: 段落间距判断系数
            min_confidence: 最低置信度过滤
            column_separator: 列分隔符
        """
        self.row_threshold_ratio = row_threshold_ratio
        self.gap_threshold_ratio = gap_threshold_ratio
        self.paragraph_spacing_ratio = paragraph_spacing_ratio
        self.min_confidence = min_confidence
        self.column_separator = column_separator

    def format(self, ocr_response: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        智能排版 OCR 结果

        Args:
            ocr_response: OCR 识别结果数组

        Returns:
            包含格式化文本和元数据的字典
        """
        # 1. 过滤低置信度文本块
        blocks, filtered_count = self._filter_blocks(ocr_response)

        if not blocks:
            return {
                'formatted_text': '',
                'metadata': {
                    'row_count': 0,
                    'column_count': 0,
                    'paragraph_count': 0,
                    'filtered_blocks': filtered_count
                }
            }

        # 2. 行聚合
        rows = self._cluster_rows(blocks)

        # 3. 每行内部按左边界排序
        for row in rows:
            row.sort_by_left()

        # 4. 检测列结构
        max_columns = max(len(row.blocks) for row in rows)

        # 5. 生成格式化文本
        formatted_text, paragraph_count = self._generate_formatted_text(rows)

        return {
            'formatted_text': formatted_text,
            'metadata': {
                'row_count': len(rows),
                'column_count': max_columns,
                'paragraph_count': paragraph_count,
                'filtered_blocks': filtered_count
            }
        }

    def _filter_blocks(self, ocr_response: List[Dict[str, Any]]) -> Tuple[List[TextBlock], int]:
        """
        过滤低置信度文本块

        Returns:
            (有效文本块列表, 被过滤的数量)
        """
        blocks = []
        filtered_count = 0

        for item in ocr_response:
            if item.get('rate', 0) < self.min_confidence:
                filtered_count += 1
                continue

            try:
                block = TextBlock(
                    text=item.get('text', ''),
                    left=float(item.get('left', 0)),
                    top=float(item.get('top', 0)),
                    right=float(item.get('right', 0)),
                    bottom=float(item.get('bottom', 0)),
                    rate=float(item.get('rate', 0))
                )
                blocks.append(block)
            except (ValueError, TypeError) as e:
                logger.warning(f"解析文本块失败: {e}")
                filtered_count += 1

        return blocks, filtered_count

    def _cluster_rows(self, blocks: List[TextBlock]) -> List[Row]:
        """
        行聚合：将垂直位置相近的文本块归为同一行
        """
        if not blocks:
            return []

        # 计算行高中位数
        heights = [block.height for block in blocks]
        median_height = self._median(heights)

        # 行聚合阈值
        row_threshold = median_height * self.row_threshold_ratio

        # 按垂直中心点排序
        sorted_blocks = sorted(blocks, key=lambda b: b.center_y)

        # 贪心聚类
        rows = []
        current_row_blocks = [sorted_blocks[0]]
        current_row_center = sorted_blocks[0].center_y

        for block in sorted_blocks[1:]:
            if abs(block.center_y - current_row_center) <= row_threshold:
                # 属于当前行
                current_row_blocks.append(block)
                # 更新行中心点（平均值）
                current_row_center = sum(b.center_y for b in current_row_blocks) / len(current_row_blocks)
            else:
                # 开始新行
                rows.append(self._create_row(current_row_blocks))
                current_row_blocks = [block]
                current_row_center = block.center_y

        # 添加最后一行
        if current_row_blocks:
            rows.append(self._create_row(current_row_blocks))

        return rows

    def _create_row(self, blocks: List[TextBlock]) -> Row:
        """创建行对象"""
        avg_top = sum(b.top for b in blocks) / len(blocks)
        avg_bottom = sum(b.bottom for b in blocks) / len(blocks)
        return Row(blocks=blocks, avg_top=avg_top, avg_bottom=avg_bottom)

    def _generate_formatted_text(self, rows: List[Row]) -> Tuple[str, int]:
        """
        生成格式化文本

        Returns:
            (格式化文本, 段落数量)
        """
        if not rows:
            return '', 0

        # 计算行间距中位数
        line_spacings = []
        for i in range(len(rows) - 1):
            spacing = rows[i + 1].avg_top - rows[i].avg_bottom
            if spacing > 0:
                line_spacings.append(spacing)

        median_spacing = self._median(line_spacings) if line_spacings else 0
        paragraph_threshold = median_spacing * self.paragraph_spacing_ratio

        # 生成文本
        lines = []
        paragraph_count = 1

        for i, row in enumerate(rows):
            # 生成行文本
            line_text = self._format_row(row)
            lines.append(line_text)

            # 判断是否需要插入空行（段落分隔）
            if i < len(rows) - 1:
                spacing = rows[i + 1].avg_top - row.avg_bottom
                if spacing > paragraph_threshold:
                    lines.append('')  # 插入空行
                    paragraph_count += 1

        formatted_text = '\n'.join(lines)
        return formatted_text, paragraph_count

    def _format_row(self, row: Row) -> str:
        """
        格式化单行文本

        处理列间距：如果同行内文本块间距较大，插入分隔符
        """
        if len(row.blocks) == 1:
            return row.blocks[0].text

        # 计算文本块之间的间距
        gaps = []
        for i in range(len(row.blocks) - 1):
            gap = row.blocks[i + 1].left - row.blocks[i].right
            if gap > 0:
                gaps.append(gap)

        if not gaps:
            # 无间距，直接拼接
            return ''.join(b.text for b in row.blocks)

        median_gap = self._median(gaps)
        gap_threshold = median_gap * self.gap_threshold_ratio

        # 根据间距决定连接方式
        parts = [row.blocks[0].text]
        for i in range(len(row.blocks) - 1):
            gap = row.blocks[i + 1].left - row.blocks[i].right

            if gap > gap_threshold:
                # 大间距：插入列分隔符
                parts.append(self.column_separator)
            elif gap > 0:
                # 小间距：插入单个空格
                parts.append(' ')
            # gap <= 0: 文本块重叠或紧邻，直接拼接

            parts.append(row.blocks[i + 1].text)

        return ''.join(parts)

    @staticmethod
    def _median(values: List[float]) -> float:
        """计算中位数"""
        if not values:
            return 0
        sorted_values = sorted(values)
        n = len(sorted_values)
        if n % 2 == 0:
            return (sorted_values[n // 2 - 1] + sorted_values[n // 2]) / 2
        else:
            return sorted_values[n // 2]


def format_ocr_text(ocr_response: List[Dict[str, Any]],
                    row_threshold_ratio: float = 0.5,
                    gap_threshold_ratio: float = 2.0,
                    paragraph_spacing_ratio: float = 1.5,
                    min_confidence: float = 0.3,
                    column_separator: str = "\t") -> Dict[str, Any]:
    """
    智能排版 OCR 识别结果

    Args:
        ocr_response: OCR 识别结果数组
        row_threshold_ratio: 行聚合阈值系数
        gap_threshold_ratio: 列间距判断系数
        paragraph_spacing_ratio: 段落间距判断系数
        min_confidence: 最低置信度过滤
        column_separator: 列分隔符

    Returns:
        包含格式化文本和元数据的字典
    """
    formatter = TextFormatter(
        row_threshold_ratio=row_threshold_ratio,
        gap_threshold_ratio=gap_threshold_ratio,
        paragraph_spacing_ratio=paragraph_spacing_ratio,
        min_confidence=min_confidence,
        column_separator=column_separator
    )

    return formatter.format(ocr_response)
