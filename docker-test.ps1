# Docker 测试脚本 - PowerShell 版本
# 用于 Windows 环境

$ErrorActionPreference = "Stop"

# 配置
$IMAGE_NAME = "wxocr"
$TAG = "latest"
$CONTAINER_NAME = "wxocr-test"
$PORT = 5000

Write-Host "========================================"
Write-Host "  WeChat OCR Docker 测试脚本" -ForegroundColor Green
Write-Host "========================================"
Write-Host ""

# 步骤1: 清理旧容器和镜像
Write-Host "[1/6] 清理旧容器和镜像..." -ForegroundColor Yellow
docker rm -f $CONTAINER_NAME 2>$null
docker rmi "${IMAGE_NAME}:${TAG}" 2>$null
Write-Host "✓ 清理完成" -ForegroundColor Green
Write-Host ""

# 步骤2: 构建镜像
Write-Host "[2/6] 构建 Docker 镜像..." -ForegroundColor Yellow
docker build -t "${IMAGE_NAME}:${TAG}" .
if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ 镜像构建成功" -ForegroundColor Green
} else {
    Write-Host "✗ 镜像构建失败" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 步骤3: 运行容器
Write-Host "[3/6] 启动容器..." -ForegroundColor Yellow
docker run -d `
    --name $CONTAINER_NAME `
    -p "${PORT}:5000" `
    -e MAX_CONCURRENT_TASKS=5 `
    -e LOG_LEVEL=INFO `
    "${IMAGE_NAME}:${TAG}"

if ($LASTEXITCODE -eq 0) {
    Write-Host "✓ 容器启动成功" -ForegroundColor Green
} else {
    Write-Host "✗ 容器启动失败" -ForegroundColor Red
    exit 1
}
Write-Host ""

# 步骤4: 等待服务就绪
Write-Host "[4/6] 等待服务就绪..." -ForegroundColor Yellow
$ready = $false
for ($i = 1; $i -le 30; $i++) {
    try {
        $response = Invoke-WebRequest -Uri "http://localhost:${PORT}/api/v1/health" -UseBasicParsing -ErrorAction SilentlyContinue
        if ($response.StatusCode -eq 200) {
            Write-Host "✓ 服务已就绪" -ForegroundColor Green
            $ready = $true
            break
        }
    } catch {
        # 忽略错误，继续等待
    }
    Write-Host "." -NoNewline
    Start-Sleep -Seconds 1
}

if (-not $ready) {
    Write-Host ""
    Write-Host "✗ 服务启动超时" -ForegroundColor Red
    docker logs $CONTAINER_NAME
    exit 1
}
Write-Host ""

# 步骤5: 运行测试
Write-Host "[5/6] 运行 API 测试..." -ForegroundColor Yellow
Write-Host ""

# 测试1: 健康检查
Write-Host "测试 1: 健康检查"
try {
    $response = Invoke-RestMethod -Uri "http://localhost:${PORT}/api/v1/health"
    if ($response.success -eq $true) {
        Write-Host "✓ 健康检查通过" -ForegroundColor Green
    } else {
        Write-Host "✗ 健康检查失败" -ForegroundColor Red
    }
} catch {
    Write-Host "✗ 健康检查失败: $_" -ForegroundColor Red
}
Write-Host ""

# 测试2: 创建测试文件
Write-Host "测试 2: 创建测试文件"
"This is a test image for OCR" | Out-File -FilePath "test.txt" -Encoding utf8
Write-Host "✓ 测试文件已创建" -ForegroundColor Green
Write-Host ""

# 测试3: 基本 OCR 请求
Write-Host "测试 3: 基本 OCR 请求"
try {
    $response = Invoke-RestMethod -Uri "http://localhost:${PORT}/api/v1/ocr" `
        -Method Post `
        -Form @{file = Get-Item "test.txt"}

    if ($response.success -eq $true) {
        Write-Host "✓ OCR 请求成功" -ForegroundColor Green
        Write-Host "处理方法: $($response.data.metadata.processing_method)"
    } else {
        Write-Host "✗ OCR 请求失败" -ForegroundColor Red
    }
} catch {
    Write-Host "✗ OCR 请求失败: $_" -ForegroundColor Red
}
Write-Host ""

# 测试4: 带参数的 OCR 请求
Write-Host "测试 4: 带参数的 OCR 请求（水印去除+纠偏）"
try {
    $response = Invoke-RestMethod -Uri "http://localhost:${PORT}/api/v1/ocr" `
        -Method Post `
        -Form @{
            file = Get-Item "test.txt"
            remove_watermark = 'true'
            watermark_color = '#ffd9d9'
            deskew = 'true'
        }

    if ($response.success -eq $true) {
        Write-Host "✓ 带参数的 OCR 请求成功" -ForegroundColor Green
        Write-Host "水印去除: $($response.data.metadata.preprocessed.watermark_removed)"
        Write-Host "图片纠偏: $($response.data.metadata.preprocessed.deskewed)"
    } else {
        Write-Host "✗ 带参数的 OCR 请求失败" -ForegroundColor Red
    }
} catch {
    Write-Host "✗ 带参数的 OCR 请求失败: $_" -ForegroundColor Red
}
Write-Host ""

# 测试5: 错误处理（无文件）
Write-Host "测试 5: 错误处理（无文件）"
try {
    $response = Invoke-RestMethod -Uri "http://localhost:${PORT}/api/v1/ocr" `
        -Method Post `
        -ErrorAction Stop
    Write-Host "✗ 应该返回错误但返回了成功" -ForegroundColor Red
} catch {
    if ($_.Exception.Response.StatusCode -eq 400) {
        Write-Host "✓ 错误处理正常（返回400）" -ForegroundColor Green
    } else {
        Write-Host "✗ 错误处理异常: $_" -ForegroundColor Red
    }
}
Write-Host ""

# 步骤6: 显示容器日志
Write-Host "[6/6] 容器日志（最后20行）:" -ForegroundColor Yellow
docker logs --tail 20 $CONTAINER_NAME
Write-Host ""

# 清理测试文件
Remove-Item "test.txt" -ErrorAction SilentlyContinue

Write-Host "========================================"
Write-Host "  测试完成！" -ForegroundColor Green
Write-Host "========================================"
Write-Host ""
Write-Host "容器状态:"
docker ps -f name=$CONTAINER_NAME
Write-Host ""
Write-Host "停止容器: docker stop $CONTAINER_NAME"
Write-Host "删除容器: docker rm $CONTAINER_NAME"
Write-Host "查看日志: docker logs -f $CONTAINER_NAME"
Write-Host "进入容器: docker exec -it $CONTAINER_NAME bash"
