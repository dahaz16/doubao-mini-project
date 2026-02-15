# Gitee 部署指南 (最新版)

本文档基于现有项目配置整理，专注于使用 Gitee 仓库进行代码部署的流程。

## 核心信息

- **代码仓库 (Gitee)**: `https://gitee.com/ah-tuo/doubao-mini-project`
- **部署平台**: Coolify (IP: `62.234.150.82`)
- **服务端口**: `8001`
- **管理后台**: `http://62.234.150.82:8001/admin/`

---

## 部署流程

### 1. 本地准备与构建 (必需)

在部署代码前，必须先在本地构建管理后台的前端资源，并将其提交到代码库中。

```bash
# 进入项目根目录
cd /Users/wangyituo/Documents/拓的文稿/项目/回忆录项目/回忆录代码项目/doubao-mini-project

# 运行构建脚本 (会自动构建前端并复制到后端静态目录)
./build-admin.sh
```

### 2. 提交代码

构建完成后，将代码（包括新构建的前端资源）提交到 Git。

```bash
# 查看变更
git status

# 添加所有变更 (确保包含 backend/static/admin 下的文件)
git add -A

# 提交
git commit -m "部署更新: [描述你的修改]"
```

### 3. 推送到 Gitee

将代码推送到 Gitee 的 `main` 分支。Coolify 配置为从 Gitee 拉取代码。

```bash
# 推送到 Gitee
git push gitee main
```
> **注意**: 如果提示需要密码，请使用你的 Gitee 账号密码。

### 4. 在 Coolify 中触发部署

1.  访问 Coolify 面板: [http://62.234.150.82:8000](http://62.234.150.82:8000)
2.  进入 **Projects** -> **memoir-project** -> **production**。
3.  点击右上角的 **"Redeploy"** 按钮。
4.  等待部署完成 (通常需要几分钟)。

---

## 验证部署

部署完成后，请进行以下检查：

1.  **API 健康检查**:
    访问 `http://62.234.150.82:8001/`，应返回 `{"status":"ok", ...}`。

2.  **管理后台**:
    访问 `http://62.234.150.82:8001/admin/`，确保能正常加载页面。

3.  **小程序配置**:
    确保小程序 `app.js` 中的 `baseUrl` 指向云端地址：
    ```javascript
    baseUrl: 'http://62.234.150.82:8001'
    ```

## 常见问题

-   **Gitee 推送失败**:如果没有权限，请检查 Gitee 账号密码是否正确。
-   **部署后后台页面空白**: 通常是因为忘记运行 `./build-admin.sh` 就直接推送了代码。务必确保 `backend/static/admin` 目录下的文件是最新的。
