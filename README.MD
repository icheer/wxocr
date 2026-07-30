# WeChat OCR API

<div align="center">

[![Docker](https://img.shields.io/badge/docker-ready-blue.svg)](https://www.docker.com/)
[![Python](https://img.shields.io/badge/python-3.12-blue.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)

**基于微信 OCR 引擎的智能文字识别服务**

支持图片和 PDF 文件的高精度识别，提供水印去除、图片纠偏等增强功能

[特性](#特性) • [快速开始](#快速开始) • [API文档](#api-文档) • [部署指南](#部署指南)

</div>

---

## 特性

### 🎯 核心功能

- ✅ **图片 OCR** - 支持 PNG、JPG、BMP、TIFF 等格式
- ✅ **PDF 智能处理** - 自动识别文档类型，选择最优处理策略
  - 纯文本 PDF：直接提取（秒级响应）
  - 扫描 PDF：整页渲染后 OCR
  - 混合 PDF：文本提取 + 图片 OCR
- ✅ **水印去除** - 指定色值或自动检测浅色水印
- ✅ **图片纠偏** - 自动检测并纠正扫描件倾斜
- ✅ **并发控制** - 限流机制保护服务稳定性
- ✅ **RESTful API** - 标准 HTTP 接口，易于集成

### 🚀 技术亮点

- **智能策略选择** - 根据页面结构自动选择处理方式（文本提取 vs OCR）
- **高性能处理** - PyMuPDF + OpenCV 优化，单页处理 < 5秒
- **容器化部署** - Docker 一键启动，跨平台支持
- **模块化设计** - 清晰的代码结构，易于扩展和维护
- **完整的错误处理** - 统一的错误响应格式和日志记录

---

## 快速开始

### 方式一：Docker（推荐）

```bash
# 1. 拉取镜像
docker pull icheerme/wxocr

# 2. 运行容器
docker run -d -p 5000:5000 --name wxocr icheerme/wxocr

# 3. 测试服务
curl http://localhost:5000/api/v1/health
```

### 方式二：本地运行

```bash
# 1. 克隆项目
git clone https://github.com/icheer/wxocr.git
cd wxocr

# 2. 安装依赖
pip install -r requirements.txt

# 3. 启动服务
python app.py

# 4. 测试服务
curl http://localhost:5000/api/v1/health
```

---

## 使用示例

### 基本图片识别

```bash
curl -X POST http://localhost:5000/api/v1/ocr \
  -F "file=@image.png"
```

### PDF 文档识别

```bash
curl -X POST http://localhost:5000/api/v1/ocr \
  -F "file=@document.pdf"
```

### 去除水印

```bash
curl -X POST http://localhost:5000/api/v1/ocr \
  -F "file=@watermarked.pdf" \
  -F "remove_watermark=true" \
  -F "watermark_color=#ffd9d9"
```

### 纠正倾斜

```bash
curl -X POST http://localhost:5000/api/v1/ocr \
  -F "file=@skewed.jpg" \
  -F "deskew=true"
```

### Python 客户端

```python
import requests

def ocr_file(file_path):
    url = 'http://localhost:5000/api/v1/ocr'
    with open(file_path, 'rb') as f:
        response = requests.post(url, files={'file': f})
    
    result = response.json()
    if result['success']:
        return result['data']['text']
    else:
        raise Exception(result['error']['message'])

# 使用
text = ocr_file('document.pdf')
print(text)
```

---

## API 文档

### 端点

| 方法 | 路径 | 说明 |
|------|------|------|
| GET | `/api/v1/health` | 健康检查 |
| POST | `/api/v1/ocr` | OCR 识别 |

### 参数

| 参数 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `file` | File | ✅ | 图片或 PDF 文件 |
| `remove_watermark` | Boolean | ❌ | 是否去除水印 |
| `watermark_color` | String | ❌ | 水印颜色（#RRGGBB） |
| `watermark_tolerance` | Integer | ❌ | 颜色容差（0-255，默认40） |
| `deskew` | Boolean | ❌ | 是否纠正倾斜 |
| `output_format` | String | ❌ | 输出格式（plain/structured） |

### 响应格式

```json
{
  "success": true,
  "data": {
    "text": "识别到的文本内容...",
    "metadata": {
      "file_type": "pdf",
      "page_count": 5,
      "processing_method": "text_extraction",
      "preprocessed": {
        "watermark_removed": true,
        "deskewed": false
      },
      "processing_time_ms": 3240
    }
  }
}
```

**完整文档**: [docs/api-spec.md](docs/api-spec.md)

---

## 部署指南

### Docker 部署

#### 1. 构建镜像

```bash
docker build -t wxocr:latest .
```

#### 2. 运行容器

```bash
docker run -d \
  --name wxocr \
  -p 5000:5000 \
  -e MAX_CONCURRENT_TASKS=5 \
  -e MAX_FILE_SIZE_MB=50 \
  -e LOG_LEVEL=INFO \
  wxocr:latest
```

#### 3. 查看日志

```bash
docker logs -f wxocr
```

#### 4. 进入容器

```bash
docker exec -it wxocr bash
```

### Docker Compose

```yaml
version: '3.8'

services:
  wxocr:
    image: golangboyme/wxocr:latest
    container_name: wxocr
    ports:
      - "5000:5000"
    environment:
      - MAX_CONCURRENT_TASKS=5
      - MAX_FILE_SIZE_MB=50
      - LOG_LEVEL=INFO
    volumes:
      - ./temp:/app/temp
      - ./logs:/app/logs
    restart: unless-stopped
```

启动：
```bash
docker-compose up -d
```

---

## 配置说明

### 环境变量

| 变量 | 默认值 | 说明 |
|------|--------|------|
| `HOST` | 0.0.0.0 | 服务监听地址 |
| `PORT` | 5000 | 服务端口 |
| `MAX_FILE_SIZE_MB` | 20 | 最大文件大小（MB） |
| `MAX_PDF_PAGES` | 50 | PDF 最大页数 |
| `MAX_CONCURRENT_TASKS` | 3 | 最大并发任务数 |
| `TEMP_DIR` | ./temp | 临时文件目录 |
| `LOG_LEVEL` | INFO | 日志级别 |
| `WATERMARK_TOLERANCE` | 40 | 默认水印容差 |
| `DESKEW_THRESHOLD` | 1.0 | 纠偏角度阈值（度） |
| `PDF_RENDER_SCALE` | 2.0 | PDF 渲染缩放倍数 |

### 配置示例

```bash
# 开发环境
export LOG_LEVEL=DEBUG
export MAX_CONCURRENT_TASKS=2
python app.py

# 生产环境
export LOG_LEVEL=WARNING
export MAX_CONCURRENT_TASKS=10
export MAX_FILE_SIZE_MB=50
python app.py
```

---

## 项目结构

```
wxocr/
├── api/                    # API 路由和验证
│   ├── routes.py          # 路由定义
│   ├── validators.py      # 参数验证
│   └── error_handlers.py  # 错误处理
├── services/              # 服务层
│   ├── pdf_processor.py   # PDF 处理
│   ├── image_processor.py # 图片预处理
│   ├── ocr_service.py     # OCR 服务
│   └── task_manager.py    # 任务管理
├── utils/                 # 工具函数
│   ├── watermark_remover.py  # 水印去除
│   ├── deskew_helper.py      # 图片纠偏
│   └── logger.py             # 日志系统
├── config/                # 配置管理
│   └── settings.py        # 应用配置
├── docs/                  # 文档
│   ├── api-spec.md        # API 规范
│   ├── implementation-plan.md  # 实施计划
│   └── windows-testing-guide.md # 测试指南
├── wx/                    # 微信 OCR 运行时
├── app.py                 # 应用入口（新版）
├── main.py                # 应用入口（旧版，兼容）
├── Dockerfile             # Docker 构建文件
├── docker-compose.yml     # Docker Compose 配置
├── requirements.txt       # Python 依赖
└── README.md             # 项目说明
```

---

## 技术栈

- **Web 框架**: Flask 3.0+
- **PDF 处理**: PyMuPDF 1.23+
- **图像处理**: OpenCV 4.8+
- **数组计算**: NumPy 1.24+
- **图片纠偏**: deskew 1.5+ / scikit-image 0.21+
- **OCR 引擎**: WeChat OCR (wcocr)
- **容器化**: Docker

---

## 性能指标

| 文件类型 | 页数/尺寸 | 预处理 | 处理时间 |
|----------|-----------|--------|----------|
| 纯文本 PDF | 10页 | 无 | < 1秒 |
| 扫描 PDF | 1页 | 无 | 3-5秒 |
| 扫描 PDF | 10页 | 无 | 30-50秒 |
| 图片 | 1920x1080 | 无 | 2-4秒 |
| 图片 | 1920x1080 | 水印+纠偏 | 4-6秒 |

**并发能力**: 默认 3 个并发任务（可配置）

---

## 开发指南

### 本地开发

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 运行测试
python test_phase1.py        # Phase 1 基础架构测试
python test_integration.py   # 集成测试

# 3. 启动开发服务器
export DEBUG=true
export LOG_LEVEL=DEBUG
python app.py
```

### 测试

```bash
# Windows
powershell -ExecutionPolicy Bypass -File docker-test.ps1

# Linux/Mac
bash docker-test.sh
```

### 代码规范

- 遵循 PEP 8 编码规范
- 使用类型注解（Type Hints）
- 编写文档字符串（Docstrings）
- 添加单元测试

---

## 常见问题

### Q: 支持哪些语言？

A: 主要支持中文和英文，依赖微信 OCR 引擎的语言能力。

### Q: 为什么 PDF 处理很快？

A: 对于纯文本 PDF，服务会直接提取文本而非 OCR，速度极快。

### Q: 如何提高识别准确率？

A: 
- 使用高分辨率图片（推荐 300 DPI）
- 启用水印去除功能
- 启用图片纠偏功能
- 确保文字清晰、对比度高

### Q: 返回 429 错误怎么办？

A: 服务器繁忙，请稍后重试。可以增加 `MAX_CONCURRENT_TASKS` 配置。

### Q: Windows 本地测试为什么返回模拟数据？

A: wcocr 是 Linux 程序，在 Windows 上会进入测试模式。实际 OCR 功能需要在 Docker 中测试。

---

## 贡献指南

欢迎贡献代码！请遵循以下步骤：

1. Fork 本仓库
2. 创建特性分支 (`git checkout -b feature/AmazingFeature`)
3. 提交更改 (`git commit -m 'Add some AmazingFeature'`)
4. 推送到分支 (`git push origin feature/AmazingFeature`)
5. 开启 Pull Request

---

## 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 致谢

本项目基于以下开源项目：

- [原版wxocr](https://github.com/golangboy/wxocr) - 微信 OCR 引擎封装
- [wechat-ocr](https://github.com/swigger/wechat-ocr) - 微信 OCR 调用演示
- [PyMuPDF](https://github.com/pymupdf/PyMuPDF) - PDF 处理库
- [OpenCV](https://github.com/opencv/opencv-python) - 图像处理库

---

## 免责声明

⚠️ **本项目仅供学习和研究使用，请勿用于商业用途。**

使用者应自行承担使用本软件的任何后果。如果您认为本项目侵犯了您的权利，请立即联系仓库所有者，我们将及时处理。

---

<div align="center">

**如果这个项目对你有帮助，请给个 ⭐️ Star 支持一下！**

[报告问题](https://github.com/icheer/wxocr/issues) • [功能建议](https://github.com/icheer/wxocr/issues)

</div>
