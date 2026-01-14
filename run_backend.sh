#!/bin/bash
echo ">>> 正在启动后端服务 (稳定性模式)..."
cd "$(dirname "$0")"
# 禁用 --reload 以防止日志写入导致的连接中断
./venv/bin/uvicorn backend.main:app --host 0.0.0.0 --port 8000
