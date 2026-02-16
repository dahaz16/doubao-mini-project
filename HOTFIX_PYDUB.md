# 🚨 紧急修复: pydub 依赖缺失

## 问题

Coolify 部署后出现错误:
```
❌ 音频转换失败: No module named 'pydub'
```

## 原因

Docker 使用了缓存的镜像层,没有重新安装 `pydub` 依赖。

## 修复

已修改 `Dockerfile`,强制重新构建依赖层。

## 立即部署

```bash
# 1. 提交修复
git add Dockerfile
git commit -m "fix: 强制重新安装 pydub 依赖"
git push

# 2. 在 Coolify 中重新部署
# 重要: 确保 Coolify 不使用缓存!
```

## 验证

部署后,在 Coolify 日志中搜索:
```
Successfully installed pydub
```

如果看到这行,说明 pydub 已正确安装。

## 测试

重新发送"你好",应该能看到:
```
[v3.4] ✅ AudioSegment 创建成功
[v3.4] ✅ MP3 导出成功
[COS] ✅✅✅ 文件上传成功!
[v3.4] ✅✅✅ AI 音频保存完全成功!
```
