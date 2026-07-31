# PDF/图片 OCR 服务实施计划

## 项目概述

基于现有的 WeChat OCR 能力，扩展支持 PDF 文档的智能处理，包括页面结构分析、可选的水印去除、图片纠偏等功能，最终输出纯文本识别结果。

## 核心需求

### 功能需求
1. **智能PDF处理**：自动判断页面结构，选择最优处理方案
   - **纯文本PDF**：直接提取文本（最快、最准确）
   - **整页扫描图**：渲染整页后OCR
   - **多图拼接**：提取图片对象分别OCR
   - **混合内容**：文本提取 + 图片OCR，结果合并

2. **图片预处理**（可选，通过API参数控制）
   - 水印去除：自动识别或指定色值去除浅色水印
   - 图片纠偏：检测并纠正扫描件的轻微倾斜

3. **并发控制**：通过限流机制保护服务稳定性

4. **统一接口**：支持图片和PDF文件输入

### 非功能需求
- **性能**：单页处理时间 < 5秒（不含预处理）
- **稳定性**：错误率 < 1%，支持优雅降级
- **可扩展性**：便于后续添加更多预处理选项

---

## 技术选型

### 核心依赖库

| 库 | 版本 | 用途 |
|---|---|---|
| `PyMuPDF (fitz)` | >= 1.23.0 | PDF解析、图片提取、页面渲染 |
| `opencv-python` | >= 4.8.0 | 图像预处理、水印去除、纠偏 |
| `numpy` | >= 1.24.0 | 图像数据处理 |
| `deskew` | >= 1.5.0 | 倾斜角度检测 |
| `scikit-image` | >= 0.21.0 | 图像旋转、变换 |
| `Flask` | >= 3.0.0 | Web框架 |
| `Pillow` | >= 10.0.0 | 图像格式转换 |

### 现有资源
- `wcocr` Python C扩展：已有的微信OCR绑定
- `wx/opt/wechat/` 目录：微信OCR二进制及依赖库

---

## 系统架构设计

### 目录结构
```
wxocr/
├── main.py                    # 原有的简单OCR接口（保留）
├── app.py                     # 新的主应用入口
├── api/
│   ├── __init__.py
│   ├── routes.py              # API路由定义
│   └── validators.py          # 请求参数验证
├── services/
│   ├── __init__.py
│   ├── pdf_processor.py       # PDF处理服务
│   ├── image_processor.py     # 图片预处理服务
│   ├── ocr_service.py         # OCR调用服务
│   └── task_manager.py        # 任务队列和限流管理
├── utils/
│   ├── __init__.py
│   ├── watermark_remover.py   # 水印去除工具
│   └── deskew_helper.py       # 图片纠偏工具
├── config/
│   ├── __init__.py
│   └── settings.py            # 配置管理
├── tests/                     # 单元测试
├── docs/
│   ├── python-lib.md          # 技术调研文档（已有）
│   ├── implementation-plan.md # 本实施计划
│   └── api-spec.md            # API接口文档（待创建）
├── references/
│   └── index.html             # OCR demo页面（已有）
├── wx/                        # 微信OCR运行时（已有）
├── temp/                      # 临时文件目录
├── requirements.txt           # Python依赖
├── Dockerfile                 # Docker构建文件
└── docker-compose.yml         # Docker编排（已有）
```

### 数据流设计

```
[客户端] 
    ↓ POST /api/ocr
[API路由层] 
    ↓ 参数验证、文件保存
[任务管理器] 
    ↓ 限流检查、任务队列
[PDF/图片处理器]
    ├─ PDF: 页面结构分析
    │   ├─ 尝试提取文本 → 有效文本? → 直接返回 ✓
    │   └─ 文本为空/无效 → 分析图片覆盖率
    │       ├─ 单张大图(>80%) → 整页渲染
    │       └─ 多图/小图 → 提取图片对象
    └─ 图片: 直接读取
    ↓
[预处理服务]（可选，仅图片OCR路径）
    ├─ 水印去除
    └─ 图片纠偏
    ↓
[OCR服务]（仅需要时）
    ↓ 调用 wcocr.ocr()
[结果聚合]
    ↓ 合并多页文本、元数据
[JSON响应] → [客户端]
```

**处理策略优先级**（从高到低）：
1. **直接文本提取**（纯文本PDF）- 最快、最准确
2. **整页渲染OCR**（影印版PDF，单张大图覆盖>80%）
3. **图片提取OCR**（混合PDF，多个图片对象）
4. **混合模式**（有文本+有图片，两者结合）

---

## API 接口设计

### 统一OCR接口

**端点**: `POST /api/ocr`

**请求**:
```http
POST /api/ocr
Content-Type: multipart/form-data

file: <binary>                          # 图片或PDF文件
remove_watermark: false                 # 是否去除水印（默认false）
watermark_color: ""                     # 水印颜色（可选，如"#ffd9d9"）
watermark_tolerance: 40                 # 颜色容差（默认40）
deskew: false                           # 是否纠偏（默认false）
output_format: "plain"                  # 输出格式：plain/structured
```

**响应（成功）**:
```json
{
  "success": true,
  "data": {
    "text": "识别到的完整文本内容...",
    "metadata": {
      "file_type": "pdf",
      "page_count": 5,
      "processing_method": "text_extraction",  # 或 "full_page_render" / "extract_images" / "mixed"
      "preprocessed": {
        "watermark_removed": false,
        "deskewed": false
      },
      "processing_time_ms": 3240
    }
  }
}
```

**响应（失败）**:
```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "服务器正忙，请稍后重试",
    "details": {
      "current_tasks": 5,
      "max_concurrent": 3
    }
  }
}
```

**错误码定义**:
- `400 BAD_REQUEST`: 参数错误、文件格式不支持
- `413 FILE_TOO_LARGE`: 文件超出大小限制
- `429 RATE_LIMIT_EXCEEDED`: 超出并发限制
- `500 INTERNAL_ERROR`: 服务器内部错误

---

## 详细实施步骤

### Phase 1: 基础架构搭建（1-2天）

#### 任务1.1: 项目重构
- [ ] 创建新的目录结构
- [ ] 迁移现有 `main.py` 代码到模块化结构
- [ ] 编写配置管理模块 `config/settings.py`
- [ ] 设置日志系统

**交付物**:
- 模块化的项目结构
- 可配置的服务参数（端口、路径、限流阈值等）

#### 任务1.2: API框架搭建
- [ ] 实现 Flask Blueprint 路由结构
- [ ] 添加请求参数验证器
- [ ] 实现统一的错误处理中间件
- [ ] 添加请求日志记录

**交付物**:
- `/api/ocr` 接口骨架
- 完整的错误处理机制

---

### Phase 2: 核心功能开发（3-5天）

#### 任务2.1: PDF处理服务
- [ ] 实现 `pdf_processor.py`：
  - `extract_text_from_page()`: 尝试提取页面文本
  - `analyze_page_structure()`: 分析页面图片覆盖率
  - `extract_images()`: 提取内嵌图片对象
  - `render_full_page()`: 整页渲染为图片
  - `process_pdf()`: 主流程，智能选择处理策略

**关键逻辑**:
```python
def analyze_page_structure(page):
    """
    判断页面结构，优先提取文本
    返回: {
        'strategy': 'text_extraction' | 'full_page_render' | 'extract_images' | 'mixed',
        'text': str,           # 提取到的文本（如有）
        'images': [...],       # 需要OCR的图片
        'text_ratio': float,   # 文本占比
        'image_coverage': float # 图片覆盖率
    }
    """
    # 第一步：尝试提取文本
    text = page.get_text().strip()
    text_length = len(text)
    
    # 第二步：分析图片
    page_area = page.rect.width * page.rect.height
    images = page.get_images(full=True)
    image_coverage = 0.0
    
    if images:
        # 计算图片总覆盖面积
        for img in images:
            xref = img[0]
            rects = page.get_image_rects(xref)
            if rects:
                img_rect = rects[0]
                image_coverage += (img_rect.width * img_rect.height) / page_area
    
    # 第三步：决策处理策略
    # 策略1: 有效文本内容且图片覆盖率低 → 直接使用文本
    if text_length > 50 and image_coverage < 0.3:
        return {
            'strategy': 'text_extraction',
            'text': text,
            'images': [],
            'text_ratio': 1.0,
            'image_coverage': image_coverage
        }
    
    # 策略2: 纯扫描页（单张大图覆盖>80%，无文本） → 整页渲染OCR
    if len(images) == 1 and image_coverage > 0.8 and text_length < 10:
        return {
            'strategy': 'full_page_render',
            'text': '',
            'images': ['full_page'],
            'text_ratio': 0.0,
            'image_coverage': image_coverage
        }
    
    # 策略3: 混合内容（有文本+有图片） → 文本提取 + 图片OCR
    if text_length > 50 and image_coverage > 0.3:
        return {
            'strategy': 'mixed',
            'text': text,
            'images': images,
            'text_ratio': 0.5,  # 估算
            'image_coverage': image_coverage
        }
    
    # 策略4: 多图或小图片 → 逐个提取图片OCR
    return {
        'strategy': 'extract_images',
        'text': text if text_length > 10 else '',
        'images': images,
        'text_ratio': 0.2,
        'image_coverage': image_coverage
    }
```

**测试用例**:
- **纯文本PDF**（可选中文字，无图片或图片极少）
- **纯扫描PDF**（每页一张大图，无可提取文本）
- **混合PDF**（可选中文字 + 内嵌图片）
- **多图页面**（多个小图片拼接）

#### 任务2.2: 图片预处理服务
- [ ] 实现 `watermark_remover.py`：
  - `remove_by_color()`: 指定色值去水印
  - `auto_detect_watermark()`: 自动识别水印
  - `remove_watermark()`: 统一入口
  
- [ ] 实现 `deskew_helper.py`：
  - `detect_skew_angle()`: 检测倾斜角度
  - `correct_skew()`: 纠正倾斜

**示例实现**:
```python
def remove_watermark(image_array, watermark_color=None, tolerance=40):
    """
    去除水印
    :param image_array: numpy数组格式的图片
    :param watermark_color: (R,G,B) 或 None（自动检测）
    :param tolerance: 颜色容差
    :return: 处理后的图片数组
    """
    if watermark_color:
        # 指定色值去除
        return remove_by_color(image_array, watermark_color, tolerance)
    else:
        # 自动检测去除
        mask = auto_detect_watermark(image_array)
        return cv2.inpaint(image_array, mask, 3, cv2.INPAINT_TELEA)
```

#### 任务2.3: OCR服务封装
- [ ] 实现 `ocr_service.py`：
  - 封装对 `wcocr.ocr()` 的调用
  - 添加异常处理和重试逻辑
  - 结果格式标准化

```python
def ocr_image(image_path: str) -> dict:
    """
    执行OCR识别
    返回: {
        'text': str,           # 纯文本
        'details': [...],      # 详细的OCR结果
        'confidence': float    # 平均置信度
    }
    """
    try:
        result = wcocr.ocr(image_path)
        # 提取文本、计算平均置信度
        return process_ocr_result(result)
    except Exception as e:
        logger.error(f"OCR failed: {e}")
        raise
```

---

### Phase 3: 任务管理与限流（1-2天）

#### 任务3.1: 任务队列管理
- [ ] 实现 `task_manager.py`：
  - 维护当前正在处理的任务计数
  - 提供任务开始/结束的上下文管理器
  - 线程安全的并发控制

**实现方案**:
```python
import threading
from contextlib import contextmanager

class TaskManager:
    def __init__(self, max_concurrent=3):
        self.max_concurrent = max_concurrent
        self.current_tasks = 0
        self.lock = threading.Lock()
    
    def can_accept_task(self):
        with self.lock:
            return self.current_tasks < self.max_concurrent
    
    @contextmanager
    def task_slot(self):
        """使用上下文管理器自动管理任务计数"""
        with self.lock:
            if self.current_tasks >= self.max_concurrent:
                raise RateLimitError("Too many concurrent tasks")
            self.current_tasks += 1
        
        try:
            yield
        finally:
            with self.lock:
                self.current_tasks -= 1

# 使用示例
task_manager = TaskManager(max_concurrent=3)

@app.route('/api/ocr', methods=['POST'])
def ocr_endpoint():
    if not task_manager.can_accept_task():
        return error_response(429, "RATE_LIMIT_EXCEEDED", ...)
    
    with task_manager.task_slot():
        # 执行OCR处理
        result = process_file(...)
    
    return jsonify(result)
```

---

### Phase 4: 集成与测试（2-3天）

#### 任务4.1: 端到端集成
- [ ] 串联所有模块，实现完整的处理流程
- [ ] 添加临时文件清理逻辑
- [ ] 实现处理进度日志

**主流程伪代码**:
```python
def process_ocr_request(file, params):
    temp_files = []
    try:
        # 1. 保存上传的文件
        input_path = save_upload_file(file)
        temp_files.append(input_path)
        
        # 2. 判断文件类型
        if is_pdf(input_path):
            images = process_pdf(input_path, params)
        else:
            images = [input_path]
        
        # 3. 预处理（可选）
        if params['remove_watermark'] or params['deskew']:
            images = [preprocess_image(img, params) for img in images]
            temp_files.extend(images)
        
        # 4. 执行OCR
        ocr_results = [ocr_image(img) for img in images]
        
        # 5. 聚合结果
        final_text = '\n\n'.join([r['text'] for r in ocr_results])
        metadata = build_metadata(ocr_results, params)
        
        return {'success': True, 'data': {'text': final_text, 'metadata': metadata}}
        
    finally:
        # 清理临时文件
        cleanup_temp_files(temp_files)
```

#### 任务4.2: 单元测试
- [ ] PDF处理模块测试
- [ ] 水印去除测试（准备带水印的测试图片）
- [ ] 纠偏测试（准备倾斜的测试图片）
- [ ] 限流机制测试

#### 任务4.3: 集成测试
- [ ] 准备多种类型的测试文件：
  - 纯扫描PDF
  - 混合PDF
  - 带水印的扫描件
  - 倾斜的图片
  - 超大文件（测试限制）
  
- [ ] 并发压力测试：模拟多个请求同时到达

---

### Phase 5: Docker化与部署（1天）

#### 任务5.1: 更新Dockerfile
- [ ] 安装新增的Python依赖
- [ ] 确保系统依赖完整（libglib2.0-0 等）
- [ ] 优化镜像大小（多阶段构建）

**Dockerfile示例**:
```dockerfile
FROM python:3.12-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    && rm -rf /var/lib/apt/lists/*

# 安装Python依赖
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

# 复制应用代码
COPY . /app/
WORKDIR /app

# 创建temp目录
RUN mkdir -p /app/temp

EXPOSE 5000

CMD ["python", "app.py"]
```

#### 任务5.2: 更新requirements.txt
```txt
flask>=3.0.0
pymupdf>=1.23.0
opencv-python>=4.8.0
numpy>=1.24.0
deskew>=1.5.0
scikit-image>=0.21.0
pillow>=10.0.0
```

#### 任务5.3: 环境变量配置
- [ ] 支持通过环境变量配置关键参数：
  - `MAX_CONCURRENT_TASKS`: 并发限制（默认3）
  - `MAX_FILE_SIZE_MB`: 文件大小限制（默认20）
  - `MAX_PDF_PAGES`: PDF页数限制（默认50）
  - `TEMP_DIR`: 临时文件目录（默认./temp）

---

### Phase 6: 文档与优化（1天）

#### 任务6.1: API文档
- [ ] 编写 `docs/api-spec.md`
- [ ] 添加使用示例（curl、Python客户端）
- [ ] 更新 README.md

#### 任务6.2: 性能优化
- [ ] 添加图片缓存（避免重复处理同一文件）
- [ ] 优化大文件处理（流式处理）
- [ ] 添加处理超时机制

---

## 风险与对策

### 风险1: 内存占用过高
**场景**: 大PDF文件一次性加载所有页面到内存

**对策**:
- 逐页处理，处理完立即释放
- 设置文件大小和页数上限
- 添加内存监控和告警

### 风险2: OCR识别率不理想
**场景**: 预处理后反而影响识别效果

**对策**:
- 预处理为可选功能，默认关闭
- 提供对比测试工具（处理前后效果对比）
- 允许调整预处理参数（阈值、容差等）

### 风险3: 并发限流过于严格
**场景**: 用户频繁遇到429错误

**对策**:
- 可配置的限流阈值
- 提供任务队列状态查询接口
- 返回预估等待时间

### 风险4: 水印自动识别误判
**场景**: 将正常内容误识别为水印并去除

**对策**:
- 优先使用指定色值方式（更可控）
- 自动识别时采用保守的阈值
- 提供预览接口（返回处理后的图片）

---

## 测试计划

### 单元测试
- PDF结构分析准确性测试
- 水印去除效果测试
- 纠偏角度检测精度测试
- 限流逻辑正确性测试

### 集成测试
- 端到端流程测试
- 异常场景测试（损坏的文件、超大文件）
- 并发请求测试

### 性能测试
- 单页PDF处理耗时：目标 < 5秒
- 10页PDF处理耗时：目标 < 30秒
- 并发3个请求时的响应时间
- 内存占用峰值：目标 < 2GB

---

## 里程碑与交付

| 里程碑 | 预计完成时间 | 交付物 |
|--------|-------------|--------|
| M1: 基础架构 | Day 2 | 模块化代码结构、API骨架 |
| M2: 核心功能 | Day 7 | PDF处理、预处理、OCR服务 |
| M3: 限流机制 | Day 9 | 任务管理器、并发控制 |
| M4: 测试完成 | Day 12 | 测试报告、性能基准 |
| M5: 生产就绪 | Day 13 | Docker镜像、完整文档 |

**总工期预估**: 10-13 工作日（约 2 周）

---

## 后续优化方向

1. **异步处理**: 对于大PDF文件，返回任务ID，支持异步查询结果
2. **批量处理**: 支持一次上传多个文件
3. **结果缓存**: 对相同文件避免重复处理
4. **增强的水印处理**: 支持位置水印（如页脚固定位置）
5. **OCR语言支持**: 扩展多语言识别能力
6. **Web界面**: 提供类似 references/index.html 的PDF处理界面

---

## 附录

### A. 配置示例

**config/settings.py**:
```python
import os

class Config:
    # 服务配置
    HOST = os.getenv('HOST', '0.0.0.0')
    PORT = int(os.getenv('PORT', 5000))
    DEBUG = os.getenv('DEBUG', 'false').lower() == 'true'
    
    # 微信OCR路径
    WCOCR_BIN_PATH = './wx/opt/wechat/wxocr'
    WCOCR_LIB_PATH = './wx/opt/wechat'
    
    # 文件限制
    MAX_FILE_SIZE_MB = int(os.getenv('MAX_FILE_SIZE_MB', 20))
    MAX_PDF_PAGES = int(os.getenv('MAX_PDF_PAGES', 50))
    ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'pdf'}
    
    # 并发控制
    MAX_CONCURRENT_TASKS = int(os.getenv('MAX_CONCURRENT_TASKS', 3))
    
    # 临时文件
    TEMP_DIR = os.getenv('TEMP_DIR', './temp')
    CLEANUP_TEMP_FILES = True
    
    # 预处理默认参数
    DEFAULT_WATERMARK_TOLERANCE = 40
    DEFAULT_DESKEW_THRESHOLD = 1.0  # 只有倾斜角度 > 1° 才纠正
```

### B. API客户端示例

**Python客户端**:
```python
import requests

def ocr_pdf(file_path, remove_watermark=False, deskew=False):
    url = 'http://localhost:5000/api/ocr'
    
    with open(file_path, 'rb') as f:
        files = {'file': f}
        data = {
            'remove_watermark': remove_watermark,
            'deskew': deskew,
            'output_format': 'plain'
        }
        
        response = requests.post(url, files=files, data=data)
        
    if response.status_code == 200:
        result = response.json()
        if result['success']:
            return result['data']['text']
        else:
            raise Exception(result['error']['message'])
    elif response.status_code == 429:
        raise Exception('服务器繁忙，请稍后重试')
    else:
        raise Exception(f'请求失败: {response.status_code}')

# 使用示例
text = ocr_pdf('./scanned-book.pdf', remove_watermark=True, deskew=True)
print(text)
```

---

## 更新日志

- 2026-07-30: 初始版本，定义项目范围和实施计划
