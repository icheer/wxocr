# Docker 镜像优化说明

## 当前镜像分析

**镜像大小**：1.1 GB

**主要组成**：
- Python 基础镜像 (python:3.12-slim): ~150-200 MB
- opencv-python (完整版): ~400-500 MB
- scikit-image: ~150-200 MB
- PyMuPDF: ~50-80 MB
- 其他 Python 包: ~30-50 MB
- wx 运行时: 80 MB
- 应用代码: <1 MB
- 系统依赖: ~50-100 MB

## 优化方案

### 1. 使用 opencv-python-headless（推荐）

**改动**：`opencv-python` → `opencv-python-headless`

**效果**：节省 200-300 MB（去除 Qt GUI 和高级 GUI 功能）

**风险**：低
- headless 版本保留所有核心图像处理功能
- 只移除了 GUI 显示相关的功能（服务端不需要）
- API 完全兼容，无需修改代码

**预期大小**：1.1 GB → 800-900 MB

### 2. 其他优化措施（已包含在 Dockerfile.optimized）

- **使用 `--no-install-recommends`**：避免安装推荐但非必需的包
- **替换开发包**：`libxrender-dev` → `libxrender1`（节省 ~10-20 MB）
- **清理 Python 缓存**：删除 `__pycache__`、`*.pyc`、`*.pyo`
- **合并 RUN 层**：减少镜像层数
- **优化 COPY 顺序**：按变化频率排序，提升构建缓存效率
- **非 root 用户**：提升安全性（可选）

### 3. 不推荐的优化（风险较高）

❌ **使用 Alpine 基础镜像**
- 需要重新编译 wcocr.so（当前是 glibc 版本）
- musl libc 兼容性问题
- 依赖包可能缺失或版本不兼容

❌ **移除 scikit-image**
- 可能影响 deskew 功能
- 需要重新实现图像预处理逻辑

❌ **使用更旧的 Python 版本**
- wcocr.so 是针对 Python 3.12 编译的

## 使用优化版 Dockerfile

### 测试优化效果

```bash
# 构建优化版镜像
docker build -f Dockerfile.optimized -t wxocr:optimized .

# 查看镜像大小
docker images wxocr

# 测试运行
docker run -d -p 5000:5000 -v /path/to/wx:/app/wx wxocr:optimized
```

### 如果测试通过，替换原 Dockerfile

```bash
# 备份原 Dockerfile
cp Dockerfile Dockerfile.backup

# 使用优化版
cp Dockerfile.optimized Dockerfile
cp requirements.optimized.txt requirements.txt
```

## 预期效果

| 版本 | 大小 | 节省 |
|------|------|------|
| 当前版本 | 1.1 GB | - |
| 优化版本 | 800-900 MB | ~200-300 MB (18-27%) |

## 验证清单

优化后需要验证以下功能：
- ✅ 图片 OCR 识别
- ✅ PDF 文件处理
- ✅ 水印移除功能
- ✅ 图像纠偏功能
- ✅ Web 界面访问

## 进一步优化（如果需要）

如果还需要更小的镜像（风险递增）：

1. **移除 scikit-image**（需要重写 deskew 逻辑）：节省 150-200 MB
2. **使用 distroless 基础镜像**：节省 50-100 MB，但调试困难
3. **压缩 wx 运行时**：如果可以的话，压缩或精简 wx 目录（80 MB）

但这些都会引入较大的不确定性和维护成本。
