# WeChat OCR API - 项目指南

本文档为 AI 助手提供项目上下文和开发指南。

## 项目概述

**WeChat OCR API** 是一个基于微信 OCR 引擎的智能文字识别服务，提供图片和 PDF 文件的高精度识别能力。

### 核心优势

- **人工干预能力**：提供 Web 界面支持在线修订 OCR 结果后再嵌入 PDF
- **极低资源占用**：无需 GPU，1核2G 云服务器即可运行
- **可视化编辑**：实时预览识别结果，支持文本块的编辑、删除、还原
- **灵活工作流**：识别、修订、嵌入三步解耦

### 适用场景

扫描档案数字化、合同文档 OCR 后人工校对、需要精确文本的法律/财务文档处理

## 技术架构

### 技术栈

**后端**：
- Flask 3.0+ (Web 框架)
- PyMuPDF 1.23+ (PDF 处理)
- OpenCV 4.8+ (图像处理)
- wcocr (微信 OCR 引擎)
- ReportLab 4.0+ / PyPDF2 3.0+ (PDF 生成)
- NumPy、scikit-image (图片纠偏)

**前端**：
- Vue 3.4+ (CDN 引入)
- PDF.js 3.11+ (PDF 渲染)
- Toastify.js 1.12+ (通知提示)

**部署**：
- Docker (推荐)
- Python 3.12+

### 项目结构

```
wxocr/
├── api/                    # API 层
│   ├── routes.py          # 路由定义 (/api/ocr, /api/embed, /api/ocr-and-embed)
│   ├── validators.py      # 请求参数验证
│   ├── auth.py            # Bearer Token 认证
│   └── error_handlers.py  # 统一错误处理
├── services/              # 业务逻辑层
│   ├── ocr_service.py     # OCR 服务封装
│   ├── pdf_processor.py   # PDF 智能处理（文本提取/渲染/策略选择）
│   ├── pdf_embedder.py    # PDF 文本嵌入（生成可搜索 PDF）
│   ├── image_processor.py # 图片预处理（水印去除、纠偏）
│   └── task_manager.py    # 并发任务管理
├── utils/                 # 工具模块
│   ├── watermark_remover.py  # 水印去除算法
│   ├── deskew_helper.py      # 图片纠偏算法
│   ├── logger.py             # 日志系统
│   └── request_helper.py     # 请求辅助函数
├── config/                # 配置管理
│   └── settings.py        # 环境变量 + 配置类
├── static/                # 前端资源
│   ├── index.html         # Web UI 主页
│   └── app.js             # Vue 3 应用逻辑
├── wx/                    # 微信 OCR 运行时（Linux 二进制）
├── temp/                  # 临时文件目录（自动创建）
├── logs/                  # 日志目录（自动创建）
├── app.py                 # 应用入口（推荐）
├── main.py                # 应用入口（旧版，向后兼容）
├── Dockerfile             # Docker 镜像构建
├── docker-compose.yml     # Docker Compose 配置
├── requirements.txt       # Python 依赖
└── README.md             # 用户文档
```

## 核心设计模式

### 1. PDF 智能处理策略

**文件**: `services/pdf_processor.py`

系统根据页面结构自动选择最优处理策略：

- **纯文本提取** (`text_extraction`): PDF 包含可提取文本且图片覆盖率 < 30%
- **整页渲染** (`full_page_render`): 扫描版 PDF，单图覆盖率 > 80%
- **图片提取** (`extract_images`): 图片覆盖率适中，逐个图片 OCR
- **混合模式** (`mixed`): 不同页面使用不同策略

**关键函数**:
- `analyze_page_structure()`: 分析页面结构决定策略
- `process_pdf()`: 主入口，返回 `PdfProcessResult`

### 2. OCR 服务封装

**文件**: `services/ocr_service.py`

对 `wcocr` 的统一封装：

```python
from services.ocr_service import ocr_image, OcrResult

result = ocr_image(image_path)
# result.text: 纯文本
# result.details: 详细结果（位置、置信度）
# result.confidence: 平均置信度
```

### 3. PDF 文本嵌入

**文件**: `services/pdf_embedder.py`

使用 PyMuPDF 将 OCR 文本以不可见文本层嵌入到图片/PDF：

- **中文字体**: `china-s` (PyMuPDF 内置)
- **非中文字体**: `helv` (Helvetica)
- **智能分段**: 自动检测中文/非中文切换混合字体

**关键函数**:
- `embed_text_to_image()`: 图片转可搜索 PDF
- `embed_text_to_pdf()`: PDF 嵌入文本层

### 4. 图像预处理管道

**核心文件**: `services/image_preprocessor.py`

统一的图像预处理工作流，支持 6 种预处理操作，按最优顺序执行：

**预处理顺序**：
```
1. 水印去除 (Watermark Removal)   - 异物最先处理
2. 自动纠偏 (Deskew)               - 避免旋转插值影响后续处理
3. 去噪 (Denoise)                  - 为后续增强做准备
4. 对比度增强 (Contrast Enhancement) - 为二值化做准备
5. 二值化 (Binarization)           - 不可逆操作，最后执行
6. 锐化 (Sharpen)                  - 仅在未二值化时执行（互斥）
```

**支持的预处理方法**：

1. **水印去除** (`utils/watermark_remover.py`)
   - 指定颜色值 + 容差
   - 自动检测浅色水印

2. **图片纠偏** (`utils/deskew_helper.py`)
   - 基于 Hough 变换检测倾斜角度
   - 仅当倾斜 > 阈值时纠正

3. **去噪** (新增)
   - `median`: 中值滤波（快速，适合椒盐噪声）
   - `fastNlMeans`: 非局部均值去噪（效果好但慢）
   - `bilateral`: 双边滤波（保留边缘）

4. **对比度增强** (新增，强烈推荐)
   - `clahe`: 自适应直方图均衡化（推荐）
   - `histogram`: 标准直方图均衡化

5. **二值化** (新增，强烈推荐)
   - `gaussian`: 自适应高斯阈值（推荐）
   - `otsu`: Otsu 自动阈值

6. **锐化** (新增)
   - Unsharp Mask 方法
   - 可调节强度 (0.5 - 2.0)
   - 与二值化互斥

**关键类和函数**：
```python
from services.image_preprocessor import PreprocessingConfig, preprocess_image

# 创建配置
config = PreprocessingConfig()
config.enhance_contrast = True
config.binarize = True

# 执行预处理
result = preprocess_image(image, config)
# result.image: 处理后的图像
# result.applied_operations: 已应用的操作列表
```

**图片和 PDF 复用**：
- 图片模式：直接应用预处理管道
- PDF 模式：每页渲染后应用相同的预处理管道
- 完全复用，无需重复代码

### 5. 并发控制

**文件**: `services/task_manager.py`

信号量机制限制并发任务数（默认 3）：

```python
from services.task_manager import task_manager

with task_manager.acquire():
    # 执行 OCR 任务
    pass
```

### 6. 认证机制

**文件**: `api/auth.py`

可选的 Bearer Token 认证：

- 环境变量 `API_KEY` 未设置：不启用认证
- 环境变量 `API_KEY` 已设置：所有 API 需要 `Authorization: Bearer <token>`

装饰器用法：
```python
@require_api_key
def protected_route():
    pass
```

## API 接口

### 核心端点

| 方法 | 路径 | 说明 | 认证 |
|------|------|------|------|
| GET | `/` | Web 界面主页 | ❌ |
| GET | `/api/health` | 健康检查 | ❌ |
| POST | `/api/ocr` | OCR 识别 | 可选 |
| POST | `/api/embed` | 嵌入文本生成 PDF | 可选 |
| POST | `/api/ocr-and-embed` | 一站式 OCR + 嵌入 | 可选 |
| GET | `/api/temp/<filename>` | 获取临时文件 | 可选 (query 参数) |
| GET | `/api/logs` | 查看日志 | 必须 |

### `/api/ocr` - OCR 识别

**请求参数**:
- `file`: 图片或 PDF 文件（必填）
- `remove_watermark`: 是否去除水印（可选，默认 false）
- `watermark_color`: 水印颜色 #RRGGBB（可选）
- `watermark_tolerance`: 颜色容差 0-255（可选，默认 40）
- `deskew`: 是否纠正倾斜（可选，默认 false）
- `denoise`: 是否去除噪点（可选，默认 false）
- `denoise_method`: 去噪方法 median/fastNlMeans/bilateral（可选，默认 median）
- `enhance_contrast`: 是否增强对比度（可选，默认 false，**推荐启用**）
- `contrast_method`: 对比度方法 clahe/histogram（可选，默认 clahe）
- `binarize`: 是否二值化（可选，默认 false，**推荐启用**）
- `binarize_method`: 二值化方法 gaussian/otsu（可选，默认 gaussian）
- `sharpen`: 是否锐化（可选，默认 false，与二值化互斥）
- `sharpen_strength`: 锐化强度 0.5-2.0（可选，默认 1.0）
- `output_format`: 输出格式 plain/structured（可选）

**预处理工作流顺序**：
```
水印去除 → 纠偏 → 去噪 → 对比度增强 → 二值化 → 锐化
```

**推荐组合**：
- 扫描件：`enhance_contrast=true` + `binarize=true`
- 老旧文档：`deskew=true` + `denoise=true` + `enhance_contrast=true` + `binarize=true`
- 模糊照片：`denoise=true` + `enhance_contrast=true` + `sharpen=true`

**响应** (图片):
```json
{
  "success": true,
  "data": {
    "text": "识别到的文本内容...",
    "width": 1920,
    "height": 1080,
    "image_path": "temp/xxx.png",
    "ocr_response": [
      {
        "text": "文本块内容",
        "rate": 0.95,
        "left": 10.0,
        "top": 20.0,
        "right": 200.0,
        "bottom": 50.0
      }
    ],
    "metadata": {
      "file_type": "image",
      "page_count": 1,
      "processing_method": "full_page_render",
      "preprocessed": {
        "watermark_removed": false,
        "deskewed": false,
        "denoised": false,
        "contrast_enhanced": true,
        "binarized": true,
        "sharpened": false
      },
      "processing_time_ms": 3240
    }
  }
}
```

**响应** (PDF):
```json
{
  "success": true,
  "data": {
    "text": "完整文本内容...",
    "pdf_path": "temp/xxx.pdf",
    "pages": [
      {
        "page_number": 1,
        "width": 595.0,
        "height": 842.0,
        "text": "第一页文本",
        "strategy": "text_extraction",
        "ocr_response": [...]
      }
    ],
    "metadata": {
      "file_type": "pdf",
      "page_count": 5,
      "processing_method": "mixed"
    }
  }
}
```

### `/api/embed` - 嵌入文本生成 PDF

**请求参数** (JSON):
- `file_path`: 临时文件路径（来自 OCR 响应，必填）
- `file_type`: 文件类型 image/pdf（必填）
- `ocr_response`: 图片模式时必填，文本块数组
- `pages`: PDF 模式时必填，页面数据数组
- `apply_preprocessing`: 是否使用预处理后的版本（可选，默认 false）

**响应**: 直接返回 PDF 文件（二进制流）

### `/api/ocr-and-embed` - 一站式接口

**功能**: 直接从图片或影印版 PDF 生成带嵌入文本的 PDF（OCR + 嵌入一步完成）

**请求参数**: 与 `/api/ocr` 相同

**响应**: 直接返回 PDF 文件（二进制流）

## 配置说明

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `HOST` | 0.0.0.0 | 服务监听地址 |
| `PORT` | 5000 | 服务端口 |
| `API_KEY` | 无 | API 认证密钥（可选） |
| `MAX_FILE_SIZE_MB` | 20 | 最大文件大小（MB） |
| `MAX_PDF_PAGES` | 50 | PDF 最大页数 |
| `MAX_CONCURRENT_TASKS` | 3 | 最大并发任务数 |
| `TEMP_DIR` | ./temp | 临时文件目录 |
| `TEMP_FILE_RETENTION` | 200 | 保留的临时文件数量 |
| `LOG_LEVEL` | INFO | 日志级别 |
| `WATERMARK_TOLERANCE` | 40 | 默认水印容差 |
| `DESKEW_THRESHOLD` | 1.0 | 纠偏角度阈值（度） |
| `PDF_RENDER_SCALE` | 2.0 | PDF 渲染缩放倍数 |

### 配置类

**文件**: `config/settings.py`

- `Config`: 基础配置
- `DevelopmentConfig`: 开发环境
- `ProductionConfig`: 生产环境

通过 `FLASK_ENV` 环境变量切换。

## 开发指南

### 本地开发环境

**Windows 注意事项**:
- `wcocr` 是 Linux 程序，Windows 本地运行会进入**测试模式**
- 测试模式返回模拟数据，实际 OCR 功能需要 Docker 测试

**启动步骤**:
```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 设置环境变量（可选）
export DEBUG=true
export LOG_LEVEL=DEBUG

# 3. 启动服务
python app.py
```

### Docker 开发

```bash
# 构建镜像
docker build -t wxocr:dev .

# 运行容器
docker run -d -p 5000:5000 \
  -v $(pwd)/temp:/app/temp \
  -v $(pwd)/logs:/app/logs \
  wxocr:dev

# 查看日志
docker logs -f <container_id>
```

### 常见开发任务

#### 1. 添加新的 API 端点

**步骤**:
1. 在 `api/routes.py` 添加路由函数
2. 添加 `@require_api_key` 装饰器（如需认证）
3. 使用 `api/validators.py` 验证请求参数
4. 调用 `services/` 中的业务逻辑
5. 返回统一格式的 JSON 响应

**示例**:
```python
@api_bp.route('/new-endpoint', methods=['POST'])
@require_api_key
def new_endpoint():
    try:
        # 验证参数
        # 调用服务
        # 返回结果
        return jsonify({'success': True, 'data': {...}})
    except Exception as e:
        return error_response('处理失败', str(e))
```

#### 2. 修改 PDF 处理策略

**文件**: `services/pdf_processor.py`

修改 `analyze_page_structure()` 中的阈值：
- `Config.MIN_TEXT_LENGTH_FOR_EXTRACTION`: 最少字符数
- `Config.MAX_IMAGE_COVERAGE_FOR_TEXT`: 文本提取的最大图片覆盖率
- `Config.MIN_IMAGE_COVERAGE_FULL_PAGE`: 整页渲染的最小单图覆盖率

#### 3. 添加新的图片预处理功能

**当前已实现的预处理功能**:
- 水印去除
- 自动纠偏
- 去除噪点（3种方法）
- 对比度增强（2种方法）
- 图像二值化（2种方法）
- 图像锐化

**如需添加新功能，步骤**:
1. 在 `services/image_preprocessor.py` 中添加新的处理函数
2. 更新 `PreprocessingConfig` 类添加新参数
3. 在 `preprocess_image()` 函数的工作流中插入新步骤（注意顺序）
4. 在 `api/validators.py` 的 `OcrRequestParams` 添加请求参数
5. 前端 `static/index.html` 和 `static/app.js` 添加 UI 控件

**预处理顺序原则**:
- 水印去除优先（异物最先处理）
- 几何变换（纠偏）在图像质量最好时进行
- 去噪在二值化前处理
- 对比度增强为二值化做准备
- 二值化最后（不可逆操作）
- 锐化与二值化互斥

#### 4. 修改临时文件清理策略

**文件**: `services/task_manager.py`

修改 `cleanup_temp_files()` 函数：
- 当前策略：保留最近 N 个文件（TEMP_FILE_RETENTION）
- 可改为基于时间的清理（使用 TEMP_FILE_MAX_AGE_HOURS）

### 代码规范

- **PEP 8**: 遵循 Python 官方编码规范
- **类型注解**: 使用 Type Hints（`typing` 模块）
- **文档字符串**: 所有函数添加 Docstrings
- **错误处理**: 使用 `try-except` 捕获异常，记录日志
- **日志级别**:
  - `logger.debug()`: 调试信息
  - `logger.info()`: 一般信息
  - `logger.warning()`: 警告信息
  - `logger.error()`: 错误信息（带 `exc_info=True`）

### 测试

**本地测试**:
```bash
# Windows
powershell -ExecutionPolicy Bypass -File docker-test.ps1

# Linux/Mac
bash docker-test.sh
```

**API 测试**:
```bash
# 健康检查
curl http://localhost:5000/api/health

# OCR 识别
curl -X POST http://localhost:5000/api/ocr \
  -F "file=@test.png"
```

## 常见问题

### Q: 为什么 Windows 本地测试返回模拟数据？

A: `wcocr` 是 Linux 程序，在 Windows 上无法运行。系统检测到 `wcocr` 初始化失败后会进入测试模式。实际 OCR 功能需要在 Docker 容器中测试。

### Q: 如何调试 PDF 处理策略？

A: 设置 `LOG_LEVEL=DEBUG`，查看 `logs/app.log` 中的详细日志：
```
分析页面结构: page_number=1, text_length=150, image_count=1, image_coverage=0.85
决定处理策略: full_page_render (原因: 存在单个大图覆盖率 > 0.8)
```

### Q: 临时文件占用太多空间怎么办？

A: 降低 `TEMP_FILE_RETENTION` 环境变量（默认 200）。系统会自动删除超过数量的旧文件。

### Q: 如何提高 OCR 识别速度？

A: 
1. 增加 `MAX_CONCURRENT_TASKS`（需要足够的 CPU 资源）
2. 降低 `PDF_RENDER_SCALE`（牺牲清晰度）
3. 对纯文本 PDF，系统会自动跳过 OCR 直接提取

### Q: 如何支持更多图片格式？

A: 修改 `config/settings.py` 中的 `ALLOWED_IMAGE_EXTENSIONS`：
```python
ALLOWED_IMAGE_EXTENSIONS = {'png', 'jpg', 'jpeg', 'bmp', 'tiff', 'webp'}
```

## 部署指南

### Docker 生产部署

```bash
# 1. 拉取镜像
docker pull icheerme/wxocr

# 2. 运行容器（生产配置）
docker run -d \
  --name wxocr \
  -p 5000:5000 \
  -e API_KEY=your_secure_secret_key \
  -e LOG_LEVEL=WARNING \
  -e MAX_CONCURRENT_TASKS=10 \
  -e MAX_FILE_SIZE_MB=50 \
  -e TEMP_FILE_RETENTION=500 \
  -v /data/wxocr/temp:/app/temp \
  -v /data/wxocr/logs:/app/logs \
  --restart unless-stopped \
  icheerme/wxocr
```

### Docker Compose

```yaml
version: '3.8'

services:
  wxocr:
    image: icheerme/wxocr:latest
    container_name: wxocr
    ports:
      - "5000:5000"
    environment:
      - API_KEY=${API_KEY}
      - MAX_CONCURRENT_TASKS=10
      - MAX_FILE_SIZE_MB=50
      - LOG_LEVEL=WARNING
      - TEMP_FILE_RETENTION=500
    volumes:
      - ./temp:/app/temp
      - ./logs:/app/logs
    restart: unless-stopped
```

### 系统要求

- **CPU**: 需要支持 AVX2 指令集（2013 年后的 Intel/AMD CPU）
- **内存**: 最低 2GB RAM
- **磁盘**: 根据 `TEMP_FILE_RETENTION` 配置预留空间

## 性能指标

| 文件类型 | 页数/尺寸 | 预处理 | 处理时间 |
|----------|-----------|--------|----------|
| 纯文本 PDF | 10页 | 无 | < 1秒 |
| 扫描 PDF | 1页 | 无 | 3-5秒 |
| 扫描 PDF | 10页 | 无 | 30-50秒 |
| 图片 | 1920x1080 | 无 | 2-4秒 |
| 图片 | 1920x1080 | 水印+纠偏 | 4-6秒 |

**并发能力**: 默认 3 个并发任务（可通过 `MAX_CONCURRENT_TASKS` 配置）

## 安全注意事项

1. **生产环境必须设置 API_KEY**
2. **文件大小限制**: 默认 20MB（`MAX_FILE_SIZE_MB`）
3. **路径遍历保护**: `/api/temp/<filename>` 端点只能访问 TEMP_DIR 内的文件
4. **临时文件清理**: 自动清理防止磁盘占满
5. **日志敏感信息**: 避免在日志中记录文件内容

## 贡献指南

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

## 许可证

MIT License - 详见 LICENSE 文件

## 致谢

- [wxocr](https://github.com/golangboy/wxocr) - 原版微信 OCR 引擎封装
- [PyMuPDF](https://github.com/pymupdf/PyMuPDF) - PDF 处理库
- [OpenCV](https://github.com/opencv/opencv-python) - 图像处理库

---

**最后更新**: 2026-08-01
