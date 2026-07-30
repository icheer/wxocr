# Windows 本地测试指南

## 概述

由于 wxocr 二进制是 Linux 程序，无法在 Windows 上运行。但我们已配置服务在 wcocr 初始化失败时自动进入**测试模式**，你可以测试API的所有行为（参数验证、错误处理、响应格式等），只是返回的是模拟数据而非真实OCR结果。

---

## 启动步骤

### 1. 安装依赖

```bash
pip install flask
```

*注：PyMuPDF、opencv等库暂时不需要安装，Phase 2实现时再装*

### 2. 启动服务

在项目根目录执行：

```bash
python app.py
```

### 3. 查看启动日志

正常情况下你会看到类似输出：

```
============================================================
启动 WeChat OCR 服务
============================================================
配置摘要: {'host': '0.0.0.0', 'port': 5000, ...}
微信OCR初始化失败（进入测试模式）: No module named 'wcocr'
⚠️  服务将以测试模式运行，OCR接口将返回模拟数据
API蓝图注册成功
错误处理器注册成功
应用创建完成
服务启动在 http://0.0.0.0:5000
```

看到 **"进入测试模式"** 即表示成功！

---

## 测试API

### 1. 健康检查

打开浏览器访问：
```
http://localhost:5000/api/v1/health
```

应该返回：
```json
{
  "success": true,
  "status": "healthy",
  "timestamp": 1722331234567
}
```

### 2. 测试 OCR 接口 - 使用 curl

#### 创建测试文件

在项目目录创建一个 `test.txt` 文件作为测试（模拟图片）：
```bash
echo "test image" > test.txt
```

#### 测试基本上传

```bash
curl -X POST http://localhost:5000/api/v1/ocr ^
  -F "file=@test.txt"
```

#### 测试完整参数

```bash
curl -X POST http://localhost:5000/api/v1/ocr ^
  -F "file=@test.txt" ^
  -F "remove_watermark=true" ^
  -F "watermark_color=#ffd9d9" ^
  -F "watermark_tolerance=50" ^
  -F "deskew=true" ^
  -F "output_format=plain"
```

**预期响应**：
```json
{
  "success": true,
  "data": {
    "text": "【模拟图片识别结果】\n这是图片中的示例文字\n用于测试OCR接口",
    "metadata": {
      "file_type": "image",
      "page_count": 1,
      "processing_method": "full_page_render",
      "preprocessed": {
        "watermark_removed": true,
        "deskewed": true
      },
      "processing_time_ms": 15,
      "test_mode": true
    }
  }
}
```

*注意 `test_mode: true` 表示这是模拟数据*

### 3. 测试 OCR 接口 - 使用 PowerShell

如果 curl 不可用，使用 PowerShell：

```powershell
# 创建测试文件
"test content" | Out-File -FilePath test.txt -Encoding utf8

# 发送请求
$response = Invoke-WebRequest -Uri http://localhost:5000/api/v1/ocr `
  -Method Post `
  -Form @{
    file = Get-Item -Path test.txt
    remove_watermark = 'true'
    deskew = 'true'
  }

# 查看响应
$response.Content | ConvertFrom-Json | ConvertTo-Json -Depth 10
```

### 4. 测试 OCR 接口 - 使用 Python

创建 `test_api_client.py`：

```python
import requests

# 测试健康检查
response = requests.get('http://localhost:5000/api/v1/health')
print("健康检查:", response.json())

# 创建测试文件
with open('test_image.png', 'wb') as f:
    f.write(b'fake image data')

# 测试OCR接口
with open('test_image.png', 'rb') as f:
    response = requests.post(
        'http://localhost:5000/api/v1/ocr',
        files={'file': f},
        data={
            'remove_watermark': 'true',
            'watermark_color': '#ffd9d9',
            'deskew': 'true'
        }
    )

print("\nOCR结果:")
import json
print(json.dumps(response.json(), indent=2, ensure_ascii=False))
```

运行：
```bash
python test_api_client.py
```

---

## 测试错误处理

### 1. 测试文件大小限制

上传超过20MB的文件应返回413错误：

```bash
# 创建21MB的测试文件
fsutil file createnew large_file.bin 22020096

curl -X POST http://localhost:5000/api/v1/ocr ^
  -F "file=@large_file.bin"
```

**预期响应**：
```json
{
  "success": false,
  "error": {
    "code": "FILE_TOO_LARGE",
    "message": "文件大小超过限制 (20MB)"
  }
}
```

### 2. 测试无效参数

```bash
curl -X POST http://localhost:5000/api/v1/ocr ^
  -F "file=@test.txt" ^
  -F "watermark_tolerance=999"
```

**预期响应**（容差超出范围）：
```json
{
  "success": false,
  "error": {
    "code": "PARAM_OUT_OF_RANGE",
    "message": "参数 watermark_tolerance 不能大于 255"
  }
}
```

### 3. 测试不支持的HTTP方法

```bash
curl -X GET http://localhost:5000/api/v1/ocr
```

**预期响应**：
```json
{
  "success": false,
  "error": {
    "code": "METHOD_NOT_ALLOWED",
    "message": "仅支持POST方法"
  }
}
```

### 4. 测试缺少文件

```bash
curl -X POST http://localhost:5000/api/v1/ocr
```

**预期响应**：
```json
{
  "success": false,
  "error": {
    "code": "NO_FILE",
    "message": "请求中未找到文件"
  }
}
```

---

## 查看日志

服务运行时的所有日志会输出到：
- **控制台**：实时查看
- **文件**：`logs/app.log`（自动创建）

可以打开另一个终端窗口实时监控日志文件：

```bash
# PowerShell
Get-Content logs\app.log -Wait

# 或者用记事本打开
notepad logs\app.log
```

---

## 常见问题

### Q: 服务无法启动，提示端口被占用

**A**: 5000端口被其他程序占用，两种解决方案：

1. 更改端口：
   ```bash
   set PORT=8080
   python app.py
   ```

2. 找到并关闭占用端口的程序：
   ```bash
   netstat -ano | findstr :5000
   taskkill /PID <进程ID> /F
   ```

### Q: curl 命令不可用

**A**: Windows 10/11 自带 curl，如果提示找不到：

1. 使用 PowerShell 的 `Invoke-WebRequest`
2. 安装 Git Bash（包含 curl）
3. 使用上面提供的 Python 测试脚本

### Q: 如何停止服务

**A**: 在运行 `python app.py` 的终端窗口按 `Ctrl+C`

---

## 测试模式 vs 生产模式

| 特性 | 测试模式（Windows） | 生产模式（Docker） |
|------|-------------------|-------------------|
| wcocr可用 | ❌ | ✅ |
| API行为测试 | ✅ | ✅ |
| 参数验证 | ✅ | ✅ |
| 错误处理 | ✅ | ✅ |
| OCR结果 | 模拟数据 | 真实识别 |
| 日志记录 | ✅ | ✅ |

**测试模式的限制**：
- OCR返回的是模拟数据，不是真实识别结果
- 无法测试实际的图片处理和识别质量

**测试模式的优势**：
- 无需Docker环境
- 快速验证API逻辑
- 开发前端/客户端时可用

---

## 下一步

完成本地测试后，可以：

1. **继续开发Phase 2** - 实现实际的OCR逻辑
2. **Docker测试** - 在Linux容器中测试真实OCR功能
3. **前端开发** - 基于API接口开发客户端

---

## 快速启动总结

```bash
# 1. 启动服务
python app.py

# 2. 新建终端窗口，测试健康检查
curl http://localhost:5000/api/v1/health

# 3. 创建测试文件
echo test > test.txt

# 4. 测试OCR接口
curl -X POST http://localhost:5000/api/v1/ocr -F "file=@test.txt"

# 5. 查看详细日志
# 回到服务运行的终端窗口查看
```

祝测试顺利！ 🚀
