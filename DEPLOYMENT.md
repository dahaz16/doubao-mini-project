# Coolify 部署指南

本文档详细说明如何在 Coolify 上部署回忆录后端服务。

## 前置条件

- ✅ Coolify 已安装并运行在 `http://62.234.150.82:8000`
- ✅ PostgreSQL 数据库已在 Coolify 中部署
- ✅ 项目代码已准备好 Dockerfile 和 .dockerignore

---

## 部署步骤

### 第一步: 在 Coolify 中创建新服务

1. **登录 Coolify**
   - 访问: `http://62.234.150.82:8000`
   - 使用你的账号密码登录

2. **进入项目**
   - 点击左侧菜单 **"Projects"**
   - 选择 **"memoir-project"** → **"production"**

3. **创建新服务**
   - 点击 **"+ Add Resource"** 或类似按钮
   - 选择 **"Docker Image"** 或 **"Git Repository"**

4. **配置服务类型**
   - 如果选择 **Git Repository**:
     - Repository URL: `https://github.com/dahaz16/doubao-mini-project`
     - Branch: `main`
     - Build Pack: **Dockerfile**
   - 如果选择 **Docker Image**:
     - 需要先在本地构建并推送到 Docker Hub

---

### 第二步: 配置环境变量

在 Coolify 的 **"Environment Variables"** 页面,添加以下变量:

```bash
# 火山引擎配置
VOLC_APPID=7689563698
VOLC_ACCESS_KEY=rUdHBaevPF1TRrp4b9ihN6cde5pAWoBt
VOLC_SECRET_KEY=BqZOfzsU7obGrdelgWvUTZMS48GCIpAD
VOLC_ASR_CLUSTER=volcengine_streaming_common
VOLC_TTS_CLUSTER=volcano_tts

# 豆包 AI 配置
ARK_API_KEY=2e94d489-1cd6-4480-aa76-962a7a7c1a46
ARK_ENDPOINT_ID=doubao-seed-1-8-251228

# 数据库配置
DATABASE_URL=postgresql://postgres:pcyj7ncWMuHWcZvbphVb4g9jtyJ1JaB5fbvsgQeoBYw0l9qJRjprTSSLczSvWBL5@62.234.150.82:5432/postgres

# 微信小程序配置
WECHAT_APPID=wx6669e0af16e6188a
WECHAT_SECRET=412ed9fc735053419c2e6b3b0f14b56b

# 腾讯云 COS 配置
COS_SECRET_ID=AKID0rNp6B3lHblhT3Rp7GCvUxDH8nHYeXCf
COS_SECRET_KEY=KROAmPyMuMbd0EH6g3CAvUqz6950rXls
COS_REGION=ap-beijing
COS_BUCKET=memoir-1259167163
```

> **注意**: 在 Coolify 中,每个环境变量需要单独添加,格式为 `KEY=VALUE`

---

### 第三步: 配置端口映射

在 **"Network"** 或 **"Ports Mappings"** 配置:

- **Container Port**: `8001`
- **Host Port**: `8001`
- **Protocol**: `TCP`

或者勾选 **"Make it publicly available"** 并设置:
- **Public Port**: `8001`

---

### 第四步: 启动服务

1. **保存配置**
   - 确认所有配置正确
   - 点击 **"Save"** 或 **"Deploy"**

2. **等待部署**
   - Coolify 会自动:
     - 拉取代码
     - 构建 Docker 镜像
     - 启动容器
   - 查看 **"Logs"** 标签页监控部署进度

3. **验证服务状态**
   - 服务状态应显示为 **"Running"** (绿色)
   - 如果失败,查看日志排查问题

---

## 验证部署

### 1. 健康检查

在浏览器或终端测试:

```bash
curl http://62.234.150.82:8001/
```

应返回:
```json
{"status":"ok","message":"后端服务运行中,已启用全局连接池。"}
```

### 2. 管理后台访问

访问: `http://62.234.150.82:8001/admin`

应该能看到管理后台界面。

### 3. API 测试

测试微信登录接口:
```bash
curl -X POST http://62.234.150.82:8001/api/wechat/login \
  -H "Content-Type: application/json" \
  -d '{"code":"test_code"}'
```

---

## 更新小程序配置

部署成功后,需要更新小程序的 API 地址。

### 修改配置文件

找到小程序中的 API 配置文件(通常在 `miniprogram/config.js` 或类似位置),将:

```javascript
// 旧地址
const API_BASE_URL = 'http://192.168.3.73:8000'
```

改为:

```javascript
// 新地址
const API_BASE_URL = 'http://62.234.150.82:8001'
```

---

## 常见问题

### Q1: 服务启动失败,日志显示 "Address already in use"

**原因**: 8001 端口被占用

**解决**:
- 在 Coolify 中检查是否有其他服务使用了 8001 端口
- 或者修改 Dockerfile 中的端口为其他值(如 8002)

### Q2: 服务启动后无法访问

**检查清单**:
1. 服务状态是否为 "Running"?
2. 端口映射是否正确配置?
3. 防火墙是否开放了 8001 端口?
4. 环境变量是否都配置正确?

### Q3: 数据库连接失败

**检查**:
- `DATABASE_URL` 环境变量是否正确
- 数据库服务是否正常运行
- 网络连接是否正常

---

## 日志查看

### 在 Coolify 中查看日志

1. 进入服务详情页
2. 点击 **"Logs"** 标签
3. 实时查看服务日志

### 常用日志过滤

- 查看错误: 搜索 `ERROR` 或 `Exception`
- 查看启动日志: 搜索 `Application startup`
- 查看请求日志: 搜索 `收到请求`

---

## 服务管理

### 重启服务

在 Coolify 服务页面:
- 点击 **"Restart"** 按钮

### 停止服务

在 Coolify 服务页面:
- 点击 **"Stop"** 按钮

### 更新代码

1. 推送代码到 GitHub
2. 在 Coolify 中点击 **"Redeploy"**
3. Coolify 会自动拉取最新代码并重新构建

---

## 后续优化建议

### 1. 配置域名(可选)

在 Coolify 中配置域名:
- 添加 DNS 记录: `api.atuo.cloud` → `62.234.150.82`
- 在 Coolify 中配置 SSL 证书(Let's Encrypt)
- 访问地址变为: `https://api.atuo.cloud`

### 2. 配置自动部署

在 GitHub 中配置 Webhook:
- 代码推送后自动触发 Coolify 重新部署

### 3. 监控告警

在 Coolify 中配置:
- 服务健康检查
- 异常告警通知

---

## 技术支持

如遇到问题:
1. 查看 Coolify 日志
2. 查看服务日志
3. 检查环境变量配置
4. 验证网络连接

部署成功后,你的服务将 7x24 小时稳定运行,不再依赖本地 Mac! 🎉
