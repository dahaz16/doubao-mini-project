# 使用 Python 3.13 官方镜像
FROM python:3.13-slim

# 设置工作目录
WORKDIR /app

# 安装系统依赖
# ffmpeg: 用于音频格式转换 (PCM -> MP3)
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

# 复制依赖文件
COPY backend/requirements.txt /app/backend/requirements.txt

# 安装 Python 依赖
RUN pip install --no-cache-dir -r /app/backend/requirements.txt

# 复制项目文件
COPY . /app

# 暴露端口 8001
EXPOSE 8001

# 设置环境变量
ENV PYTHONUNBUFFERED=1

# 启动命令
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8001"]
