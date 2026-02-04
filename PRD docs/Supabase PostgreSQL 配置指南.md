# Supabase PostgreSQL 配置指南 🚀

> **目标：** 5 分钟内获取免费的 PostgreSQL 数据库连接信息

---

## 第一步：注册 Supabase 账号

1. **打开浏览器**，访问：https://supabase.com/

2. **点击右上角 "Start your project"** 或 **"Sign Up"**

3. **选择登录方式**（任选其一）：
   - 使用 GitHub 账号登录（推荐，最快）
   - 使用 Google 账号登录
   - 使用邮箱注册

4. **授权登录**
   - 如果选择 GitHub/Google，点击"授权"即可
   - 如果用邮箱，需要验证邮箱

---

## 第二步：创建新项目

登录成功后，你会看到控制台页面：

1. **点击 "New Project"**（新建项目）

2. **填写项目信息**：
   
   | 字段 | 填写内容 | 说明 |
   |---|---|---|
   | **Organization** | 选择默认组织 | 如果是第一次用，会自动创建 |
   | **Name** | `memoir-project` | 项目名称（随便起） |
   | **Database Password** | 设置一个密码 | **重要！请记住这个密码** |
   | **Region** | 选择 **Singapore (Southeast Asia)** | 离中国最近的服务器 |
   | **Pricing Plan** | 选择 **Free** | 免费版 |

3. **点击 "Create new project"**

4. **等待 1-2 分钟**
   - 页面会显示 "Setting up project..."
   - 等待进度条完成

---

## 第三步：获取数据库连接信息

项目创建完成后：

1. **点击左侧菜单的 "Project Settings"**（项目设置）
   - 图标是一个齿轮 ⚙️

2. **点击 "Database"** 标签页

3. **找到 "Connection string" 区域**

4. **选择 "URI" 模式**（默认就是）

5. **复制连接字符串**
   - 会看到类似这样的字符串：
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.xxxxx.supabase.co:5432/postgres
   ```

6. **替换密码**
   - 将 `[YOUR-PASSWORD]` 替换为你在第二步设置的密码
   - 例如，如果你的密码是 `MyPass123`，最终字符串是：
   ```
   postgresql://postgres:MyPass123@db.xxxxx.supabase.co:5432/postgres
   ```

---

## 第四步：记录信息

请将以下信息填入表格：

| 项目 | 你的信息 |
|---|---|
| **数据库类型** | PostgreSQL |
| **完整连接字符串** | `postgresql://postgres:密码@db.xxxxx.supabase.co:5432/postgres` |
| **主机地址** | `db.xxxxx.supabase.co` |
| **端口** | `5432` |
| **数据库名** | `postgres` |
| **用户名** | `postgres` |
| **密码** | 你设置的密码 |

---

## 第五步：验证连接（可选）

如果你想确认数据库可以连接，可以：

1. **在 Supabase 控制台左侧点击 "SQL Editor"**

2. **点击 "New query"**

3. **输入测试 SQL**：
   ```sql
   SELECT version();
   ```

4. **点击 "Run"**
   - 如果看到 PostgreSQL 版本信息，说明数据库正常工作

---

## 完成！🎉

**现在请将完整的连接字符串发给我**，格式如下：

```
postgresql://postgres:你的密码@db.xxxxx.supabase.co:5432/postgres
```

我会立即开始配置后端连接！

---

## 常见问题

### Q1: 忘记密码怎么办？
**A:** 在 Project Settings → Database → Reset database password

### Q2: 连接字符串在哪里？
**A:** Project Settings → Database → Connection string → URI

### Q3: 免费版有什么限制？
**A:** 
- 500MB 数据库空间（够用）
- 每月 50 万次请求（够用）
- 7 天不活跃会暂停（访问一次就恢复）

### Q4: 数据会丢失吗？
**A:** 不会，Supabase 会自动备份数据

---

## 下一步

拿到连接字符串后，我会：
1. 安装 PostgreSQL 驱动
2. 修改后端配置
3. 创建数据库表结构
4. 测试连接

**准备好了就把连接字符串发给我吧！** 🚀
