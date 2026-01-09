#!/bin/bash
echo ">>> 正在启动后端服务，请稍候..."
# 进入脚本所在目录，防止路径错误
cd "$(dirname "$0")"
# 直接使用虚拟环境中的 uvicorn 启动
./venv/bin/uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000
