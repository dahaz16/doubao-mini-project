# Gitee 提交代码备忘录

## 项目路径
```
/Users/wangyituo/Documents/拓的文稿/项目/回忆录项目/回忆录代码项目/doubao-mini-project
```

## 推荐开发流程:"本地测试,测好再部署"

### 1. 日常开发 - 使用本地环境

#### 启动本地后端
```bash
cd /Users/wangyituo/Documents/拓的文稿/项目/回忆录项目/回忆录代码项目/doubao-mini-project
./run_backend.sh
```

#### 访问管理后台
后端启动后,直接在浏览器访问: **http://localhost:8000/admin/**

**注意**: 管理后台已集成在后端中,不需要单独启动开发服务器。

#### 配置小程序连接本地
编辑 `miniprogram/app.js`:
```javascript
globalData: {
  baseUrl: 'http://192.168.3.73:8000'  // 本地开发
}
```

**优点**:
- ✅ 修改后端代码后立即生效(热重载)
- ✅ 实时查看日志
- ✅ 调试方便
- ✅ 不需要等待部署
- ✅ 管理后台和小程序都能正常工作

### 2. 测试通过后 - 部署到云端

#### 提交代码到 Git
```bash
cd /Users/wangyituo/Documents/拓的文稿/项目/回忆录项目/回忆录代码项目/doubao-mini-project

# 查看修改
git status

# 添加所有修改
git add -A

# 提交
git commit -m "描述你的修改"

# 推送到 GitHub
git push origin main

# 推送到 Gitee (用于 Coolify 部署)
git push gitee main
```

**注意**: 如果 `git push gitee` 提示需要密码,输入你的 Gitee 密码即可。

#### 在 Coolify 部署
1. 访问 Coolify 管理页面
2. 进入项目详情
3. 点击 "Redeploy"
4. 等待 5-10 分钟

#### 构建管理后台(部署前)
```bash
cd /Users/wangyituo/Documents/拓的文稿/项目/回忆录项目/回忆录代码项目/doubao-mini-project

# 构建管理后台
./build-admin.sh

# 提交构建后的文件
git add backend/static
git commit -m "Update admin frontend build"
git push origin main
git push gitee main
```

**注意**: 管理后台需要先构建再部署,构建后的文件在 `backend/static/` 目录。

#### 配置小程序连接云端
编辑 `miniprogram/app.js`:
```javascript
globalData: {
  baseUrl: 'http://62.234.150.82:8001'  // 云端部署
}
```

#### 访问云端管理后台
部署完成后访问: `http://62.234.150.82:8001/admin`

### 3. 环境切换技巧

可以在 `app.js` 中添加开关:
```javascript
const isDev = true;  // 开发模式开关

App({
  globalData: {
    baseUrl: isDev 
      ? 'http://192.168.3.73:8000'      // 本地
      : 'http://62.234.150.82:8001'     // 云端
  }
})
```

需要部署时,只需将 `isDev` 改为 `false` 即可。

## Git 仓库信息

- **GitHub**: https://github.com/dahaz16/doubao-mini-project
- **Gitee**: https://gitee.com/ah-tuo/doubao-mini-project
- **Coolify 使用**: Gitee 仓库

## 常见问题

### Q: 本地后端启动失败?
A: 检查 `.env` 文件是否存在,包含所有必要的环境变量。

### Q: 小程序连接本地失败?
A: 确保:
1. 本地后端正在运行
2. 手机和电脑在同一 WiFi
3. IP 地址 `192.168.3.73` 正确

### Q: Gitee 推送失败?
A: 使用以下命令重新推送:
```bash
git push https://gitee.com/ah-tuo/doubao-mini-project.git main
```
输入用户名 `ah-tuo` 和密码。

## 部署检查清单

部署前确保:
- [ ] 本地测试通过
- [ ] 代码已提交到 Git
- [ ] 已推送到 Gitee
- [ ] Coolify 环境变量配置完整
- [ ] 小程序 baseUrl 已改为云端地址
