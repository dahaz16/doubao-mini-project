# 🔍 Coolify 部署后日志诊断指南

## 📋 问题背景

本地环境音频录制功能正常,但 Coolify 部署后 **100% 失败**。

## 🎯 诊断流程

部署后,如果音频仍然没有保存成功,请按以下步骤查看日志:

### 步骤 1: 获取 Coolify 后端日志

在 Coolify 控制台:
1. 进入项目页面
2. 点击 "Logs" 标签
3. 选择后端服务的日志
4. 复制最近的日志内容

### 步骤 2: 搜索关键日志标记

在日志中搜索以下关键字(按顺序):

#### 🎵 音频保存流程开始
```
搜索: "[v3.4] 🎵 开始处理 AI 音频保存流程"
```

**期望看到**:
```
[v3.4] 🎵 开始处理 AI 音频保存流程...
[v3.4] 📊 full_audio_buffer 大小: 234567 bytes
[v3.4] 📊 ai_text_id: 123
```

**如果看不到这些日志**:
- ❌ 问题在 TTS 阶段,音频根本没有生成
- 👉 需要查看 TTS 相关日志

#### 📤 PCM 转 MP3
```
搜索: "[v3.4] 📤 PCM 转换 MP3"
```

**期望看到**:
```
[v3.4] ✅ 条件满足,开始转换和上传...
[v3.4] 📤 PCM 转换 MP3 中... 大小: 234567 bytes
[v3.4] ✅ AudioSegment 创建成功
[v3.4] ✅ MP3 导出成功, 大小: 58912 bytes
```

**如果在这里失败**:
- ❌ 可能是 `pydub` 或 `ffmpeg` 依赖问题
- 👉 检查 Dockerfile 中是否安装了 ffmpeg

#### 🚀 COS 上传
```
搜索: "[COS] 🚀 开始上传文件"
```

**期望看到**:
```
[COS] 🚀 开始上传文件...
[COS] 📊 文件大小: 58912 bytes
[COS] 📝 文件名: tts/user_id/20260216_123456_789012.mp3
[COS] 🔧 环境变量检查:
[COS]   - COS_BUCKET: ✅ memoir-1259167163
[COS]   - COS_REGION: ✅ ap-beijing
[COS]   - COS_SECRET_ID: ✅ 已设置
[COS]   - COS_SECRET_KEY: ✅ 已设置
[COS] ✅ COS 客户端创建成功
[COS] 📍 最终 Key: tts/user_id/20260216_123456_789012.mp3
[COS] 📤 开始上传到 COS: tts/...
[COS] ✅✅✅ 文件上传成功!
[COS] 🔗 URL: https://memoir-1259167163.cos.ap-beijing.myqcloud.com/...
```

**如果环境变量未设置**:
- ❌ Coolify 环境变量配置问题
- 👉 检查 Coolify 项目设置中的环境变量

**如果 COS 上传失败**:
- ❌ 可能是网络问题或 COS 密钥错误
- 👉 查看完整堆栈信息

#### 💾 数据库保存
```
搜索: "[v3.4] 💾 开始保存到数据库"
```

**期望看到**:
```
[v3.4] ✅ COS 上传成功: https://memoir-1259167163.cos.ap-beijing.myqcloud.com/...
[v3.4] 💾 开始保存到数据库...
[v3.4] 📊 保存参数: user_id=xxx, speaker_type=1, text_id=123
✅ 保存语音文件: AI, url=https://memoir-1259167163.cos.ap-beijing.myqcloud.com/..., id=456
[v3.4] ✅✅✅ AI 音频保存完全成功! voice_id=456, url=...
```

**如果数据库保存失败**:
- ❌ 可能看到重试日志:
  ```
  ⚠️ 保存语音文件失败 (尝试 1/3): server closed the connection unexpectedly, 将在 0.5s 后重试...
  ```
- 👉 如果 3 次都失败,说明数据库连接有问题

#### ❌ 错误日志
```
搜索: "❌❌❌"
```

这会找到所有严重错误,每个错误都会包含:
- 错误信息
- 上下文信息(user_id, text_id, 文件大小等)
- 完整堆栈跟踪

## 🔍 常见问题诊断

### 问题 1: 环境变量未设置

**日志特征**:
```
[COS]   - COS_BUCKET: ❌ 未设置
```

**解决方案**:
1. 在 Coolify 项目设置中添加环境变量
2. 确保变量名完全一致:`COS_BUCKET`, `COS_REGION`, `COS_SECRET_ID`, `COS_SECRET_KEY`
3. 重新部署

### 问题 2: ffmpeg 未安装

**日志特征**:
```
[v3.4] ❌❌❌ Audio Save/Convert Error: ...ffmpeg...
```

**解决方案**:
检查 `Dockerfile` 是否包含:
```dockerfile
RUN apt-get update && apt-get install -y ffmpeg
```

### 问题 3: 数据库连接超时

**日志特征**:
```
⚠️ 保存语音文件失败 (尝试 1/3): server closed the connection unexpectedly
⚠️ 保存语音文件失败 (尝试 2/3): server closed the connection unexpectedly
❌ 保存语音文件失败 (3 次尝试后): server closed the connection unexpectedly
```

**解决方案**:
1. 检查 PostgreSQL 的 `max_connections` 设置
2. 检查网络连接是否稳定
3. 考虑增加数据库超时时间

### 问题 4: TTS 音频为空

**日志特征**:
```
[v3.4] 📊 full_audio_buffer 大小: 0 bytes
[v3.4] ⚠️ full_audio_buffer 为空,跳过音频保存
```

**解决方案**:
- 问题在 TTS 阶段,需要查看 TTS 相关日志
- 搜索 `[TTS` 或 `synthesize` 相关日志

## 📊 成功的完整日志示例

```
[v3.4] 🎵 开始处理 AI 音频保存流程...
[v3.4] 📊 full_audio_buffer 大小: 234567 bytes
[v3.4] 📊 ai_text_id: 123
[v3.4] ✅ 条件满足,开始转换和上传...
[v3.4] 📤 PCM 转换 MP3 中... 大小: 234567 bytes
[v3.4] ✅ AudioSegment 创建成功
[v3.4] ✅ MP3 导出成功, 大小: 58912 bytes
[v3.4] 📝 文件名: tts/user_id/20260216_123456_789012.mp3
[COS] 🚀 开始上传文件...
[COS] 📊 文件大小: 58912 bytes
[COS] 🔧 环境变量检查:
[COS]   - COS_BUCKET: memoir-1259167163
[COS]   - COS_REGION: ap-beijing
[COS]   - COS_SECRET_ID: ✅ 已设置
[COS]   - COS_SECRET_KEY: ✅ 已设置
[COS] ✅ COS 客户端创建成功
[COS] 📍 最终 Key: tts/user_id/20260216_123456_789012.mp3
[COS] 📤 开始上传到 COS: tts/user_id/20260216_123456_789012.mp3
[COS] ✅✅✅ 文件上传成功!
[COS] 🔗 URL: https://memoir-1259167163.cos.ap-beijing.myqcloud.com/tts/user_id/20260216_123456_789012.mp3
[v3.4] ✅ COS 上传成功: https://memoir-1259167163.cos.ap-beijing.myqcloud.com/...
[v3.4] 💾 开始保存到数据库...
[v3.4] 📊 保存参数: user_id=xxx, speaker_type=1, text_id=123
✅ 保存语音文件: AI, url=https://memoir-1259167163.cos.ap-beijing.myqcloud.com/..., id=456
[v3.4] ✅✅✅ AI 音频保存完全成功! voice_id=456, url=...
[v3.4] 📊 最终统计: PCM=234567B, MP3=58912B, 压缩率=25.1%
```

## 🎯 快速诊断命令

如果您能访问 Coolify 服务器,可以使用以下命令:

```bash
# 查看最近的音频保存流程
docker logs <container_id> 2>&1 | grep -A 20 "🎵 开始处理 AI 音频保存流程"

# 查看所有错误
docker logs <container_id> 2>&1 | grep "❌❌❌"

# 查看 COS 环境变量检查
docker logs <container_id> 2>&1 | grep -A 5 "环境变量检查"

# 查看数据库保存重试
docker logs <container_id> 2>&1 | grep "保存语音文件失败"
```

## 📞 反馈格式

如果部署后仍有问题,请提供以下信息:

1. **完整的音频保存流程日志** (从 `🎵 开始处理` 到 `✅✅✅ 完全成功` 或错误信息)
2. **环境变量检查结果** (COS 相关的 4 个变量)
3. **错误堆栈** (如果有 `❌❌❌` 错误)

这样我就能快速定位问题!
