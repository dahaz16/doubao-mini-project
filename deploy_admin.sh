#!/bin/bash
# 管理后台前端自动部署脚本

set -e  # 遇到错误立即退出

echo "🚀 开始构建管理后台前端..."

# 进入前端目录
cd "$(dirname "$0")/admin-frontend"

# 构建前端
echo "📦 正在构建前端..."
npm run build

# 部署到后端静态目录
echo "📂 正在部署到后端..."
rm -rf ../backend/static/admin
cp -r dist ../backend/static/admin

echo "✅ 部署完成！"
echo "🌐 请访问: http://localhost:8000/admin/"
echo ""
echo "💡 提示: 如果浏览器有缓存，请按 Cmd+Shift+R 强制刷新"
