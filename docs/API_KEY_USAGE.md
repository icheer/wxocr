# API_KEY 认证使用说明

## 概述

本服务支持可选的 API Key 认证机制。当设置了 `API_KEY` 环境变量时，所有对 `/api/v1/ocr` 接口的请求都需要携带正确的 Bearer token。

## 配置方式

### 1. 设置环境变量

**Docker 运行时：**
```bash
docker run -d \
  -p 5000:5000 \
  -e API_KEY="your-secret-key-here" \
  -v /path/to/wx:/app/wx \
  your-image-name
```

**本地运行时：**
```bash
# Linux/Mac
export API_KEY="your-secret-key-here"
python app.py

# Windows PowerShell
$env:API_KEY = "your-secret-key-here"
python app.py

# Windows CMD
set API_KEY=your-secret-key-here
python app.py
```

**Docker Compose：**
```yaml
services:
  wxocr:
    image: your-image-name
    ports:
      - "5000:5000"
    environment:
      - API_KEY=your-secret-key-here
    volumes:
      - /path/to/wx:/app/wx
```

### 2. 不设置 API_KEY

如果不设置 `API_KEY` 环境变量，服务将**不启用认证**，任何请求都可以直接访问 OCR 接口。

## 使用方式

### Web 界面

访问服务主页 `http://your-server:5000/` 时：

1. 如果服务端配置了 API_KEY，页面顶部会显示 "API Key" 输入框
2. 在输入框中输入正确的 API Key
3. API Key 会自动保存在浏览器的 localStorage 中，下次访问无需重新输入
4. 上传文件进行识别时，会自动在请求头中携带 Bearer token

### API 调用

**curl 示例：**
```bash
# 携带 Bearer token
curl -X POST http://localhost:5000/api/v1/ocr \
  -H "Authorization: Bearer your-secret-key-here" \
  -F "file=@/path/to/image.jpg" \
  -F "remove_watermark=false" \
  -F "deskew=false"
```

**Python 示例：**
```python
import requests

url = "http://localhost:5000/api/v1/ocr"
headers = {
    "Authorization": "Bearer your-secret-key-here"
}
files = {
    "file": open("/path/to/image.jpg", "rb")
}
data = {
    "remove_watermark": "false",
    "deskew": "false"
}

response = requests.post(url, headers=headers, files=files, data=data)
print(response.json())
```

**JavaScript/Fetch 示例：**
```javascript
const formData = new FormData();
formData.append('file', fileInput.files[0]);
formData.append('remove_watermark', 'false');

const response = await fetch('/api/v1/ocr', {
  method: 'POST',
  headers: {
    'Authorization': 'Bearer your-secret-key-here'
  },
  body: formData
});

const result = await response.json();
console.log(result);
```

## 错误响应

### 缺少认证信息
```json
{
  "code": 401,
  "message": "缺少认证信息",
  "data": null
}
```

### 认证格式错误
```json
{
  "code": 401,
  "message": "认证格式错误，应为: Bearer <token>",
  "data": null
}
```

### 认证失败
```json
{
  "code": 401,
  "message": "认证失败",
  "data": null
}
```

## 安全建议

1. **使用强密码**：API Key 应该是一个足够复杂的随机字符串（建议至少 32 位）
2. **HTTPS 传输**：生产环境中应该使用 HTTPS 来保护 API Key 在传输过程中不被窃取
3. **定期更换**：建议定期更换 API Key
4. **避免硬编码**：不要在代码中硬编码 API Key，应该使用环境变量或配置文件
5. **访问日志**：启用访问日志来监控 API 使用情况

## 生成安全的 API Key

**Linux/Mac：**
```bash
openssl rand -hex 32
# 或
python3 -c "import secrets; print(secrets.token_urlsafe(32))"
```

**Windows PowerShell：**
```powershell
[Convert]::ToBase64String((1..32 | ForEach-Object { Get-Random -Maximum 256 }))
```

**Python：**
```python
import secrets
api_key = secrets.token_urlsafe(32)
print(api_key)
```

## 常见问题

### Q: 如何禁用认证？
A: 不设置 `API_KEY` 环境变量即可。

### Q: 可以同时支持多个 API Key 吗？
A: 当前版本只支持单个 API Key。如需多用户认证，建议在前面加一层反向代理（如 Nginx）或 API 网关。

### Q: 忘记了 API Key 怎么办？
A: API Key 是通过环境变量设置的，检查服务启动时的环境变量配置即可。如果无法找回，重新设置一个新的 API Key 并重启服务。

### Q: API Key 保存在哪里？
A: 服务端：通过环境变量 `API_KEY` 设置，重启后需要重新设置
Web 界面：保存在浏览器的 localStorage 中，清除浏览器数据会丢失

### Q: 健康检查接口需要认证吗？
A: 不需要。`/api/v1/health` 接口不需要认证，可以直接访问。
