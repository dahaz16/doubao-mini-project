#!/bin/bash

# 管理后台构建脚本

echo "🔨 开始构建管理后台..."

# 进入前端目录
cd admin-frontend

# 安装依赖（如果需要）
if [ ! -d "node_modules" ]; then
  echo "📦 安装依赖..."
  npm install
fi

# 构建前端
echo "⚙️ 构建前端项目..."
npm run build

# 清理旧的静态文件
echo "🧹 清理旧文件..."
rm -rf ../backend/static/admin

# 复制构建产物到后端
echo "📁 复制文件到后端..."
mkdir -p ../backend/static/admin
cp -r dist/* ../backend/static/admin/

echo "✅ 管理后台构建完成！"
echo "📍 访问地址: http://你的局域网IP:8000/admin"
