# API 接口规范

## 概述

WeChat OCR API 提供基于微信 OCR 引擎的文字识别服务，支持图片和 PDF 文件的智能处理。

- **基础URL**: `http://localhost:5000`
- **API版本**: v1
- **数据格式**: JSON
- **字符编码**: UTF-8

---

## 认证

当前版本无需认证（内部服务）。如需部署到公网，建议添加 API Key 或 JWT 认证。

---

## 接口列表

### 1. 健康检查

检查服务是否正常运行。

**端点**: `GET /api/health`

**请求示例**:
```bash
curl http://localhost:5000/api/health
```

**响应示例**:
```json
{
  "success": true,
  "status": "healthy",
  "timestamp": 1722331234567
}
```

**状态码**:
- `200` - 服务正常

---

### 2. OCR 识别

对图片或 PDF 文件执行 OCR 识别。

**端点**: `POST /api/ocr`

**Content-Type**: `multipart/form-data`

#### 请求参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| `file` | File | ✅ | - | 图片或PDF文件 |
| `remove_watermark` | Boolean | ❌ | false | 是否去除水印 |
| `watermark_color` | String | ❌ | - | 水印颜色（#RRGGBB格式） |
| `watermark_tolerance` | Integer | ❌ | 40 | 颜色容差（0-255） |
| `deskew` | Boolean | ❌ | false | 是否纠正倾斜 |
| `output_format` | String | ❌ | plain | 输出格式（plain/structured） |

#### 文件要求

**支持的图片格式**:
- PNG (.png)
- JPEG (.jpg, .jpeg)
- BMP (.bmp)
- TIFF (.tiff)

**支持的文档格式**:
- PDF (.pdf)

**文件限制**:
- 图片最大: 10MB
- PDF最大: 20MB
- PDF最多: 50页

#### 请求示例

**基本请求（仅图片）**:
```bash
curl -X POST http://localhost:5000/api/ocr \
  -F "file=@image.png"
```

**PDF文件（自动智能处理）**:
```bash
curl -X POST http://localhost:5000/api/ocr \
  -F "file=@document.pdf"
```

**去除水印（指定颜色）**:
```bash
curl -X POST http://localhost:5000/api/ocr \
  -F "file=@watermarked.pdf" \
  -F "remove_watermark=true" \
  -F "watermark_color=#ffd9d9" \
  -F "watermark_tolerance=50"
```

**图片纠偏**:
```bash
curl -X POST http://localhost:5000/api/ocr \
  -F "file=@skewed.jpg" \
  -F "deskew=true"
```

**完整参数**:
```bash
curl -X POST http://localhost:5000/api/ocr \
  -F "file=@complex.pdf" \
  -F "remove_watermark=true" \
  -F "watermark_color=#ffd9d9" \
  -F "watermark_tolerance=40" \
  -F "deskew=true" \
  -F "output_format=plain"
```

#### 响应示例

**成功响应**:
```json
{
  "success": true,
  "data": {
    "text": "识别到的完整文本内容...",
    "metadata": {
      "file_type": "pdf",
      "page_count": 5,
      "processing_method": "text_extraction",
      "preprocessed": {
        "watermark_removed": true,
        "deskewed": false
      },
      "processing_time_ms": 3240,
      "test_mode": false
    }
  }
}
```

**字段说明**:

| 字段 | 类型 | 说明 |
|------|------|------|
| `success` | Boolean | 请求是否成功 |
| `data.text` | String | 识别的纯文本内容 |
| `data.metadata.file_type` | String | 文件类型（image/pdf） |
| `data.metadata.page_count` | Integer | 页数 |
| `data.metadata.processing_method` | String | 处理方法（见下文） |
| `data.metadata.preprocessed` | Object | 预处理信息 |
| `data.metadata.processing_time_ms` | Integer | 处理耗时（毫秒） |
| `data.metadata.test_mode` | Boolean | 是否为测试模式 |

**处理方法（processing_method）**:
- `text_extraction` - 直接提取文本（纯文本PDF）
- `full_page_render` - 整页渲染后OCR（扫描PDF）
- `extract_images` - 提取图片对象后OCR
- `mixed` - 混合模式（文本提取 + 图片OCR）

#### 状态码

| 状态码 | 说明 |
|--------|------|
| `200` | 成功 |
| `400` | 请求参数错误 |
| `413` | 文件过大 |
| `429` | 超出并发限制 |
| `500` | 服务器错误 |

#### 错误响应

**参数验证错误（400）**:
```json
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "参数 watermark_tolerance 不能大于 255"
  }
}
```

**缺少文件（400）**:
```json
{
  "success": false,
  "error": {
    "code": "NO_FILE",
    "message": "请求中未找到文件"
  }
}
```

**文件类型不支持（400）**:
```json
{
  "success": false,
  "error": {
    "code": "INVALID_FILE_TYPE",
    "message": "不支持的文件类型，仅支持: png, jpg, jpeg, pdf, bmp, tiff"
  }
}
```

**文件过大（413）**:
```json
{
  "success": false,
  "error": {
    "code": "FILE_TOO_LARGE",
    "message": "文件大小超过限制 (20MB)"
  }
}
```

**超出并发限制（429）**:
```json
{
  "success": false,
  "error": {
    "code": "RATE_LIMIT_EXCEEDED",
    "message": "服务器正忙，请稍后重试",
    "details": {
      "current_tasks": 3,
      "max_concurrent": 3
    }
  }
}
```

**服务器错误（500）**:
```json
{
  "success": false,
  "error": {
    "code": "OCR_FAILED",
    "message": "OCR处理失败: 具体错误信息"
  }
}
```

---

## 错误码列表

| 错误码 | HTTP状态 | 说明 |
|--------|----------|------|
| `NO_FILE` | 400 | 请求中未找到文件 |
| `EMPTY_FILENAME` | 400 | 文件名为空 |
| `INVALID_FILE_TYPE` | 400 | 不支持的文件类型 |
| `VALIDATION_ERROR` | 400 | 参数验证失败 |
| `PARAM_OUT_OF_RANGE` | 400 | 参数超出范围 |
| `INVALID_PARAM_TYPE` | 400 | 参数类型错误 |
| `INVALID_COLOR_FORMAT` | 400 | 颜色格式无效 |
| `INVALID_OUTPUT_FORMAT` | 400 | 输出格式无效 |
| `NOT_FOUND` | 404 | 资源不存在 |
| `METHOD_NOT_ALLOWED` | 405 | HTTP方法不允许 |
| `FILE_TOO_LARGE` | 413 | 文件过大 |
| `RATE_LIMIT_EXCEEDED` | 429 | 超出并发限制 |
| `INTERNAL_ERROR` | 500 | 服务器内部错误 |
| `OCR_FAILED` | 500 | OCR处理失败 |
| `OCR_PROCESS_ERROR` | 500 | OCR处理错误 |
| `UNEXPECTED_ERROR` | 500 | 未预期的错误 |

---

## 客户端示例

### Python

```python
import requests

def ocr_file(file_path, remove_watermark=False, deskew=False):
    """
    调用 OCR API
    
    Args:
        file_path: 文件路径
        remove_watermark: 是否去除水印
        deskew: 是否纠偏
    
    Returns:
        dict: API响应
    """
    url = 'http://localhost:5000/api/ocr'
    
    with open(file_path, 'rb') as f:
        files = {'file': f}
        data = {
            'remove_watermark': str(remove_watermark).lower(),
            'deskew': str(deskew).lower()
        }
        
        response = requests.post(url, files=files, data=data)
        response.raise_for_status()
        
        return response.json()

# 使用示例
result = ocr_file('document.pdf', remove_watermark=True, deskew=True)
if result['success']:
    print(result['data']['text'])
else:
    print(f"错误: {result['error']['message']}")
```

### JavaScript (Node.js)

```javascript
const FormData = require('form-data');
const fs = require('fs');
const axios = require('axios');

async function ocrFile(filePath, options = {}) {
  const form = new FormData();
  form.append('file', fs.createReadStream(filePath));
  
  if (options.removeWatermark) {
    form.append('remove_watermark', 'true');
    if (options.watermarkColor) {
      form.append('watermark_color', options.watermarkColor);
    }
  }
  
  if (options.deskew) {
    form.append('deskew', 'true');
  }
  
  try {
    const response = await axios.post(
      'http://localhost:5000/api/ocr',
      form,
      { headers: form.getHeaders() }
    );
    
    return response.data;
  } catch (error) {
    throw new Error(`OCR失败: ${error.response?.data?.error?.message || error.message}`);
  }
}

// 使用示例
(async () => {
  const result = await ocrFile('document.pdf', {
    removeWatermark: true,
    watermarkColor: '#ffd9d9',
    deskew: true
  });
  
  if (result.success) {
    console.log(result.data.text);
  } else {
    console.error('错误:', result.error.message);
  }
})();
```

### cURL

```bash
# 基本使用
curl -X POST http://localhost:5000/api/ocr \
  -F "file=@document.pdf"

# 带所有参数
curl -X POST http://localhost:5000/api/ocr \
  -F "file=@document.pdf" \
  -F "remove_watermark=true" \
  -F "watermark_color=#ffd9d9" \
  -F "watermark_tolerance=40" \
  -F "deskew=true" \
  -F "output_format=plain"

# 保存结果到文件
curl -X POST http://localhost:5000/api/ocr \
  -F "file=@document.pdf" \
  -o result.json

# 提取纯文本
curl -X POST http://localhost:5000/api/ocr \
  -F "file=@document.pdf" \
  | jq -r '.data.text'
```

---

## 配置参数

### 环境变量

| 变量名 | 默认值 | 说明 |
|--------|--------|------|
| `HOST` | 0.0.0.0 | 服务监听地址 |
| `PORT` | 5000 | 服务端口 |
| `MAX_FILE_SIZE_MB` | 20 | 最大文件大小（MB） |
| `MAX_PDF_PAGES` | 50 | PDF最大页数 |
| `MAX_CONCURRENT_TASKS` | 3 | 最大并发任务数 |
| `TEMP_DIR` | ./temp | 临时文件目录 |
| `LOG_LEVEL` | INFO | 日志级别 |
| `WATERMARK_TOLERANCE` | 40 | 默认水印容差 |
| `DESKEW_THRESHOLD` | 1.0 | 纠偏角度阈值（度） |
| `PDF_RENDER_SCALE` | 2.0 | PDF渲染缩放倍数 |

### 使用示例

```bash
# Docker 启动时配置
docker run -d \
  -p 5000:5000 \
  -e MAX_CONCURRENT_TASKS=5 \
  -e MAX_FILE_SIZE_MB=50 \
  -e LOG_LEVEL=DEBUG \
  wxocr:latest

# 命令行启动时配置
export MAX_CONCURRENT_TASKS=5
export LOG_LEVEL=DEBUG
python app.py
```

---

## 性能指标

### 处理时间（参考值）

| 文件类型 | 页数/尺寸 | 预处理 | 预估时间 |
|----------|-----------|--------|----------|
| 纯文本PDF | 10页 | 无 | < 1秒 |
| 扫描PDF | 1页 | 无 | 3-5秒 |
| 扫描PDF | 10页 | 无 | 30-50秒 |
| 图片 | 1920x1080 | 无 | 2-4秒 |
| 图片 | 1920x1080 | 水印+纠偏 | 4-6秒 |

### 并发能力

- **默认**: 3个并发任务
- **推荐**: 根据服务器配置调整（CPU核心数 × 1-2）
- **限制**: 超出并发限制返回 429 错误

---

## 最佳实践

### 1. 文件处理

- **纯文本PDF**: 无需任何预处理参数，速度最快
- **扫描PDF**: 自动整页渲染，无需手动指定
- **带水印**: 优先使用指定颜色模式（更精确）
- **倾斜扫描件**: 启用纠偏功能

### 2. 错误处理

```python
import requests
import time

def ocr_with_retry(file_path, max_retries=3):
    """带重试的OCR调用"""
    for attempt in range(max_retries):
        try:
            response = requests.post(
                'http://localhost:5000/api/ocr',
                files={'file': open(file_path, 'rb')},
                timeout=60
            )
            
            if response.status_code == 429:
                # 超出限制，等待后重试
                time.sleep(2 ** attempt)
                continue
            
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.Timeout:
            if attempt == max_retries - 1:
                raise
            time.sleep(1)
    
    raise Exception('Max retries exceeded')
```

### 3. 批量处理

```python
from concurrent.futures import ThreadPoolExecutor
import requests

def ocr_batch(file_paths, max_workers=3):
    """批量处理文件"""
    def process_file(path):
        response = requests.post(
            'http://localhost:5000/api/ocr',
            files={'file': open(path, 'rb')}
        )
        return path, response.json()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        results = list(executor.map(process_file, file_paths))
    
    return results
```

---

## 常见问题

### Q: 支持哪些语言？

A: 当前版本使用微信OCR引擎，主要支持中文和英文。

### Q: 如何提高识别准确率？

A: 
- 使用高分辨率图片（推荐 300 DPI）
- 对带水印的文档启用水印去除
- 对倾斜的扫描件启用纠偏功能
- 确保文字清晰、对比度高

### Q: 为什么返回 429 错误？

A: 服务器正在处理的任务数达到上限。请稍后重试，或联系管理员增加并发限制。

### Q: PDF 处理很慢怎么办？

A: 
- 检查PDF是否为纯文本（可直接提取，速度快）
- 减少PDF页数（拆分大文件）
- 增加服务器并发限制

### Q: 如何调试问题？

A: 
1. 检查服务日志：`docker logs -f wxocr-container`
2. 设置 `LOG_LEVEL=DEBUG` 查看详细日志
3. 使用健康检查端点确认服务状态

---

## 更新日志

### v1.0.0 (2026-07-30)
- ✅ 初始版本发布
- ✅ 支持图片和PDF文件OCR
- ✅ 智能PDF处理（4种策略）
- ✅ 水印去除功能
- ✅ 图片纠偏功能
- ✅ 并发限流机制

---

## 联系支持

- **GitHub**: [项目仓库](https://github.com/yiGmMk/wxocr)
- **问题反馈**: 提交 GitHub Issue
- **文档**: `/docs` 目录

---

**最后更新**: 2026-07-30
