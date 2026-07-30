FROM python:3.12-slim

# 安装系统依赖
RUN apt-get update && apt-get install -y \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    libgomp1 \
    libgl1 \
    && rm -rf /var/lib/apt/lists/*

# 设置工作目录
WORKDIR /app

# 复制依赖文件并安装
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r /app/requirements.txt

# 复制 wcocr Python 扩展
COPY wcocr.cpython-312-x86_64-linux-gnu.so /app/wcocr.cpython-312-x86_64-linux-gnu.so

# 复制微信 OCR 运行时
COPY wx /app/wx

# 复制应用代码
COPY api /app/api
COPY services /app/services
COPY utils /app/utils
COPY config /app/config
COPY static /app/static
COPY app.py /app/app.py
COPY main.py /app/main.py

# 创建必要的目录
RUN mkdir -p /app/temp /app/logs

# 设置环境变量
ENV PYTHONUNBUFFERED=1
ENV HOST=0.0.0.0
ENV PORT=5000

# 暴露端口
EXPOSE 5000

# 启动命令（使用新版 app.py）
CMD ["python", "app.py"]