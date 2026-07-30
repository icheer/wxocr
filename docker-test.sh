#!/bin/bash
# Docker 测试脚本 - 自动化构建、运行和测试

set -e  # 遇到错误立即退出

# 颜色输出
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  WeChat OCR Docker 测试脚本${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""

# 配置
IMAGE_NAME="wxocr"
TAG="latest"
CONTAINER_NAME="wxocr-test"
PORT=5000

# 步骤1: 清理旧容器和镜像
echo -e "${YELLOW}[1/6] 清理旧容器和镜像...${NC}"
docker rm -f $CONTAINER_NAME 2>/dev/null || true
docker rmi $IMAGE_NAME:$TAG 2>/dev/null || true
echo -e "${GREEN}✓ 清理完成${NC}"
echo ""

# 步骤2: 构建镜像
echo -e "${YELLOW}[2/6] 构建 Docker 镜像...${NC}"
docker build -t $IMAGE_NAME:$TAG .
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 镜像构建成功${NC}"
else
    echo -e "${RED}✗ 镜像构建失败${NC}"
    exit 1
fi
echo ""

# 步骤3: 运行容器
echo -e "${YELLOW}[3/6] 启动容器...${NC}"
docker run -d \
    --name $CONTAINER_NAME \
    -p $PORT:5000 \
    -e MAX_CONCURRENT_TASKS=5 \
    -e LOG_LEVEL=INFO \
    $IMAGE_NAME:$TAG

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ 容器启动成功${NC}"
else
    echo -e "${RED}✗ 容器启动失败${NC}"
    exit 1
fi
echo ""

# 步骤4: 等待服务就绪
echo -e "${YELLOW}[4/6] 等待服务就绪...${NC}"
for i in {1..30}; do
    if curl -s http://localhost:$PORT/api/v1/health > /dev/null 2>&1; then
        echo -e "${GREEN}✓ 服务已就绪${NC}"
        break
    fi
    if [ $i -eq 30 ]; then
        echo -e "${RED}✗ 服务启动超时${NC}"
        docker logs $CONTAINER_NAME
        exit 1
    fi
    echo -n "."
    sleep 1
done
echo ""

# 步骤5: 运行测试
echo -e "${YELLOW}[5/6] 运行 API 测试...${NC}"
echo ""

# 测试1: 健康检查
echo "测试 1: 健康检查"
RESPONSE=$(curl -s http://localhost:$PORT/api/v1/health)
if echo "$RESPONSE" | grep -q "healthy"; then
    echo -e "${GREEN}✓ 健康检查通过${NC}"
else
    echo -e "${RED}✗ 健康检查失败${NC}"
    echo "响应: $RESPONSE"
fi
echo ""

# 测试2: 创建测试文件
echo "测试 2: 创建测试文件"
echo "This is a test image for OCR" > test.txt
echo -e "${GREEN}✓ 测试文件已创建${NC}"
echo ""

# 测试3: 基本 OCR 请求
echo "测试 3: 基本 OCR 请求"
RESPONSE=$(curl -s -X POST http://localhost:$PORT/api/v1/ocr \
    -F "file=@test.txt")
if echo "$RESPONSE" | grep -q "success"; then
    echo -e "${GREEN}✓ OCR 请求成功${NC}"
    echo "响应: $(echo $RESPONSE | jq -c '.data.metadata')"
else
    echo -e "${RED}✗ OCR 请求失败${NC}"
    echo "响应: $RESPONSE"
fi
echo ""

# 测试4: 带参数的 OCR 请求
echo "测试 4: 带参数的 OCR 请求（水印去除+纠偏）"
RESPONSE=$(curl -s -X POST http://localhost:$PORT/api/v1/ocr \
    -F "file=@test.txt" \
    -F "remove_watermark=true" \
    -F "watermark_color=#ffd9d9" \
    -F "deskew=true")
if echo "$RESPONSE" | grep -q "success"; then
    echo -e "${GREEN}✓ 带参数的 OCR 请求成功${NC}"
    PREPROCESSED=$(echo $RESPONSE | jq '.data.metadata.preprocessed')
    echo "预处理: $PREPROCESSED"
else
    echo -e "${RED}✗ 带参数的 OCR 请求失败${NC}"
    echo "响应: $RESPONSE"
fi
echo ""

# 测试5: 错误处理（无文件）
echo "测试 5: 错误处理（无文件）"
RESPONSE=$(curl -s -X POST http://localhost:$PORT/api/v1/ocr)
if echo "$RESPONSE" | grep -q "NO_FILE"; then
    echo -e "${GREEN}✓ 错误处理正常${NC}"
else
    echo -e "${RED}✗ 错误处理异常${NC}"
    echo "响应: $RESPONSE"
fi
echo ""

# 测试6: 不支持的 HTTP 方法
echo "测试 6: 不支持的 HTTP 方法"
RESPONSE=$(curl -s -X GET http://localhost:$PORT/api/v1/ocr)
if echo "$RESPONSE" | grep -q "METHOD_NOT_ALLOWED"; then
    echo -e "${GREEN}✓ HTTP 方法限制正常${NC}"
else
    echo -e "${RED}✗ HTTP 方法限制异常${NC}"
    echo "响应: $RESPONSE"
fi
echo ""

# 步骤6: 显示容器日志
echo -e "${YELLOW}[6/6] 容器日志（最后20行）:${NC}"
docker logs --tail 20 $CONTAINER_NAME
echo ""

# 清理测试文件
rm -f test.txt

echo -e "${GREEN}========================================${NC}"
echo -e "${GREEN}  测试完成！${NC}"
echo -e "${GREEN}========================================${NC}"
echo ""
echo "容器状态:"
docker ps -f name=$CONTAINER_NAME
echo ""
echo "停止容器: docker stop $CONTAINER_NAME"
echo "删除容器: docker rm $CONTAINER_NAME"
echo "查看日志: docker logs -f $CONTAINER_NAME"
echo "进入容器: docker exec -it $CONTAINER_NAME bash"
