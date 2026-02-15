# 采访页交互流程完整时序分析

## 概览

本文档详细分析从用户点击"讲述"按钮到 AI 回复完成后自动开始下一轮录音的完整交互流程，包括每个步骤的触发时机、UI 变化和音效播放。

---

## 流程 1：用户点击"讲述"按钮开始录音

### 时序图

```
用户点击"讲述"按钮
    ↓ (0ms - 立即)
handleMicToggle() 被调用
    ↓ (0ms - 立即)
startRecordingLogic() 被调用
    ↓ (0ms - 立即)
🔊 播放 start_recording.wav 音效
    ↓ (0ms - 立即)
🎨 UI 切换到 recording 状态（显示录音控件）
    ↓ (0ms - 立即)
清空上一轮字幕内容
    ↓ (0ms - 立即)
连接 ASR WebSocket（异步）
    ↓ (等待 800ms)
WebSocket 连接成功
    ↓ (0ms - 立即)
startRecording() 被调用
    ↓ (0ms - 立即)
启动录音倒计时（每秒更新一次）
    ↓ (0ms - 立即)
启动录音管理器 recorderManager.start()
    ↓ (录音中...)
实时接收 ASR 识别结果，更新 userInput
```

### 详细说明

| 时间点 | 事件 | UI 变化 | 音效 | 代码位置 |
|--------|------|---------|------|----------|
| **T+0ms** | 用户点击按钮 | - | - | `handleMicToggle()` |
| **T+0ms** | 调用录音逻辑 | - | - | `startRecordingLogic()` |
| **T+0ms** | **播放音效** | - | **🔊 start_recording.wav** | `playSoundEffect('start_recording')` |
| **T+0ms** | **显示录音界面** | **显示取消/发送按钮、倒计时** | - | `setData({ status: 'recording' })` |
| **T+0ms** | 连接 WebSocket | - | - | `connectASRWebSocket()` |
| **T+800ms** | WebSocket 连接成功 | - | - | `socket.onOpen()` |
| **T+800ms** | 启动录音 | 倒计时开始 | - | `startRecording()` |
| **T+800ms+** | 录音中 | 实时显示识别文字 | - | ASR 实时更新 |

### 🔍 问题分析

**音效播放时机：T+0ms** ✅ 立即播放  
**UI 显示时机：T+0ms** ✅ 立即显示  
**实际录音开始：T+800ms** ⚠️ 有 800ms 延迟（等待 WebSocket）

**用户感知：**
- ✅ 点击按钮后立即听到音效
- ✅ 点击按钮后立即看到录音界面
- ⚠️ 但实际录音要等 800ms 后才开始（用户可能无感知，因为 UI 已经显示了）

---

## 流程 2：用户点击"发送"按钮

### 时序图

```
用户点击"发送"按钮（右侧绿色箭头）
    ↓ (0ms - 立即)
handleMicToggle() 被调用（status === 'recording'）
    ↓ (0ms - 立即)
停止录音管理器 recorderManager.stop()
    ↓ (0ms - 立即)
🎨 UI 切换到 idle 状态
    ↓ (0ms - 立即)
🎨 字幕背景开始淡出动画
    ↓ (异步等待录音文件生成)
recorderManager.onStop() 回调被触发
    ↓ (0ms - 立即)
关闭 ASR WebSocket
    ↓ (0ms - 立即)
生成最终识别文本
    ↓ (等待 500ms - 确保 UI 更新完成)
handleSend() 被调用
    ↓ (0ms - 立即)
🔊 播放 send_message.wav 音效
    ↓ (0ms - 立即)
connectToChatSocket() 被调用
    ↓ (0ms - 立即)
创建对话 WebSocket 连接
    ↓ (异步等待连接)
WebSocket 连接成功
    ↓ (0ms - 立即)
发送用户消息到后端
    ↓ (等待后端响应)
接收 AI 文本流，逐字显示
    ↓ (同时)
接收 AI 音频流，实时播放
```

### 详细说明

| 时间点 | 事件 | UI 变化 | 音效 | 代码位置 |
|--------|------|---------|------|----------|
| **T+0ms** | 用户点击发送 | - | - | `handleMicToggle()` |
| **T+0ms** | 停止录音 | - | - | `recorderManager.stop()` |
| **T+0ms** | **UI 切换** | **隐藏录音控件，字幕淡出** | - | `setData({ status: 'idle' })` |
| **T+?ms** | 录音停止回调 | - | - | `recorderManager.onStop()` |
| **T+?ms+500ms** | 调用发送逻辑 | - | - | `handleSend()` |
| **T+?ms+500ms** | **播放音效** | - | **🔊 send_message.wav** | `playSoundEffect('send_message')` |
| **T+?ms+500ms** | 连接对话 WebSocket | - | - | `connectToChatSocket()` |
| **T+?ms+500ms+?** | WebSocket 连接成功 | - | - | `chatSocket.onOpen()` |
| **T+?ms+500ms+?** | 发送消息 | - | - | `chatSocket.send()` |
| **T+?ms+500ms+?+?** | 接收 AI 回复 | **逐字显示文本** | - | `onMessage()` |

### 🔍 问题分析

**音效播放时机：T+?ms+500ms** ⚠️ 有延迟  
**延迟原因：**
1. 录音停止是异步的（需要等待系统处理）
2. 录音停止后有 **500ms 的固定延迟**（`setTimeout(..., 500)`）
3. 然后才播放音效

**用户感知：**
- ⚠️ 点击发送按钮后，要等一会才听到音效
- ⚠️ 延迟时间 = 录音停止处理时间 + 500ms

---

## 流程 3：AI 回复完成后自动开始录音

### 时序图

```
后端发送 text_finish 消息
    ↓ (0ms - 立即)
chatSocket.onMessage() 接收到 text_finish
    ↓ (0ms - 立即)
🎨 UI 切换到 idle 状态
    ↓ (0ms - 立即)
计算 TTS 音频播放剩余时间
    delay = (nextStartTime - audioCtx.currentTime) * 1000
    ↓ (等待 delay 毫秒)
setTimeout 定时器触发
    ↓ (0ms - 立即)
startRecordingLogic() 被调用
    ↓ (0ms - 立即)
🔊 播放 start_recording.wav 音效
    ↓ (0ms - 立即)
🎨 UI 切换到 recording 状态（显示录音控件）
    ↓ (0ms - 立即)
连接 ASR WebSocket（异步）
    ↓ (等待 800ms)
WebSocket 连接成功
    ↓ (0ms - 立即)
启动录音
```

### 详细说明

| 时间点 | 事件 | UI 变化 | 音效 | 代码位置 |
|--------|------|---------|------|----------|
| **T+0ms** | 收到 text_finish | - | - | `chatSocket.onMessage()` |
| **T+0ms** | 计算延迟时间 | - | - | `delay = (nextStartTime - currentTime) * 1000` |
| **T+0ms** | 设置定时器 | - | - | `setTimeout(..., delay)` |
| **T+delay** | TTS 播放完毕 | - | - | - |
| **T+delay** | 定时器触发 | - | - | `autoRecordTimer` |
| **T+delay** | **播放音效** | - | **🔊 start_recording.wav** | `playSoundEffect('start_recording')` |
| **T+delay** | **显示录音界面** | **显示录音控件** | - | `setData({ status: 'recording' })` |
| **T+delay+800ms** | 启动录音 | 倒计时开始 | - | `startRecording()` |

### 🔍 问题分析

**音效播放时机：T+delay** ✅ TTS 播放完毕后立即播放  
**UI 显示时机：T+delay** ✅ TTS 播放完毕后立即显示  
**实际录音开始：T+delay+800ms** ⚠️ 有 800ms 延迟

**用户感知：**
- ✅ TTS 播放完毕后立即听到音效
- ✅ TTS 播放完毕后立即看到录音界面
- ⚠️ 但实际录音要等 800ms 后才开始

---

## 完整流程时序图（从说话到再说话）

```
┌─────────────────────────────────────────────────────────────────┐
│ 第 1 轮：用户讲述                                                │
└─────────────────────────────────────────────────────────────────┘

T0: 用户点击"讲述"
    ├─ T0+0ms:   🔊 播放 start_recording.wav
    ├─ T0+0ms:   🎨 显示录音界面（取消/发送按钮）
    ├─ T0+800ms: 🎤 开始录音
    └─ T0+800ms+: 📝 实时显示 ASR 识别文字

T1: 用户点击"发送"
    ├─ T1+0ms:   🛑 停止录音
    ├─ T1+0ms:   🎨 隐藏录音界面，字幕淡出
    ├─ T1+?ms:   📦 录音文件生成完成
    ├─ T1+?ms+500ms: 🔊 播放 send_message.wav
    ├─ T1+?ms+500ms: 📡 连接对话 WebSocket
    └─ T1+?ms+500ms+?: 📤 发送消息到后端

┌─────────────────────────────────────────────────────────────────┐
│ AI 处理与回复                                                    │
└─────────────────────────────────────────────────────────────────┘

T2: 后端开始处理
    ├─ T2+?ms: 📝 接收 AI 文本流，逐字显示
    ├─ T2+?ms: 🔊 接收 AI 音频流，实时播放
    └─ T2+?ms: ✅ 收到 text_finish 消息

┌─────────────────────────────────────────────────────────────────┐
│ 第 2 轮：自动开始录音                                            │
└─────────────────────────────────────────────────────────────────┘

T3: TTS 播放完毕（T2 + delay）
    ├─ T3+0ms:   🔊 播放 start_recording.wav
    ├─ T3+0ms:   🎨 显示录音界面
    ├─ T3+800ms: 🎤 开始录音
    └─ T3+800ms+: 📝 实时显示 ASR 识别文字
```

---

## 🎯 性能瓶颈分析

### 1. **发送音效延迟最严重** ⚠️⚠️⚠️

**当前流程：**
```
点击发送 → 停止录音（异步）→ 等待 500ms → 播放音效
```

**延迟时间：** 录音停止处理时间 + **500ms**

**优化建议：**
```javascript
// 在 handleMicToggle() 中，点击发送时立即播放音效
handleMicToggle() {
    if (this.data.status === 'recording') {
        // 🔊 立即播放发送音效（在停止录音之前）
        this.playSoundEffect('send_message');
        
        // 停止录音
        this.recorderManager.stop();
        // ...
    }
}
```

### 2. **录音启动有 800ms 延迟** ⚠️

**原因：** 等待 ASR WebSocket 连接

**影响：**
- 用户点击"讲述"后，虽然立即看到录音界面，但实际录音要等 800ms
- 如果用户立即开始说话，前 800ms 的内容会丢失

**优化建议：**
- 减少延迟到 300-500ms（测试 WebSocket 实际连接时间）
- 或者在页面加载时预先建立 WebSocket 连接（保持连接）

### 3. **自动录音的延迟计算可能不准确** ⚠️

**当前逻辑：**
```javascript
const delay = Math.max(0, (this.nextStartTime - this.audioCtx.currentTime) * 1000);
```

**问题：**
- 如果 `nextStartTime` 计算不准确，可能导致音效播放时 TTS 还在播放
- 或者 TTS 已经播放完很久了才触发

---

## 💡 优化建议总结

### 优先级 1：修复发送音效延迟（最明显的问题）

**修改位置：** `handleMicToggle()` 函数

**修改方案：** 将音效播放移到停止录音之前

```javascript
handleMicToggle() {
    if (this.data.status === 'recording') {
        // 🔊 立即播放发送音效
        this.playSoundEffect('send_message');
        
        // 停止录音
        this.recorderManager.stop();
        clearInterval(this.data.timer);
        
        // 触发字幕背景淡出动画
        this.setData({
            status: 'idle',
            userSubtitleFading: true
        });
        
        console.log("用户停止录音，字幕背景开始淡出");
    } else {
        // 开始录音
        this.startRecordingLogic();
    }
}
```

**同时删除 `handleSend()` 中的音效播放：**

```javascript
handleSend() {
    const textToSend = this.data.userInput;
    if (!textToSend || textToSend.trim() === "") {
        wx.showToast({ title: '请先说话', icon: 'none' });
        return;
    }

    console.log("发送消息:", textToSend);

    // 🔊 删除这一行（已在 handleMicToggle 中播放）
    // this.playSoundEffect('send_message');
    
    // 连接对话WebSocket
    this.connectToChatSocket(textToSend);
}
```

### 优先级 2：减少 WebSocket 连接延迟

**修改位置：** `startRecordingLogic()` 函数

**修改方案：** 将延迟从 800ms 减少到 500ms（需要测试）

```javascript
// 延迟启动录音，确保 WebSocket 已连接
setTimeout(() => {
    if (this.data.socketOpen) {
        this.startRecording();
    } else {
        console.error("WebSocket 未连接，无法开始录音");
        // 连接失败，恢复 idle 状态
        this.setData({ status: 'idle' });
        wx.showToast({
            title: '连接失败，请重试',
            icon: 'none'
        });
    }
}, 500); // 从 800ms 改为 500ms
```

### 优先级 3：删除 handleSend 前的 500ms 延迟

**修改位置：** `recorderManager.onStop()` 回调

**当前代码：**
```javascript
// 延迟发送（确保 UI 更新完成）
setTimeout(() => {
    this.handleSend();
}, 500);
```

**优化方案：** 删除延迟或减少到 100ms

```javascript
// 立即发送（UI 已在 handleMicToggle 中更新）
this.handleSend();
```

---

## 📊 优化前后对比

| 操作 | 优化前延迟 | 优化后延迟 | 改善 |
|------|-----------|-----------|------|
| 点击"讲述" → 听到音效 | 0ms ✅ | 0ms ✅ | 无变化 |
| 点击"讲述" → 看到界面 | 0ms ✅ | 0ms ✅ | 无变化 |
| 点击"讲述" → 开始录音 | 800ms ⚠️ | 500ms ⚠️ | **减少 300ms** |
| 点击"发送" → 听到音效 | ~500-800ms ❌ | 0ms ✅ | **减少 500-800ms** |
| TTS 完成 → 听到音效 | 0ms ✅ | 0ms ✅ | 无变化 |
| TTS 完成 → 看到界面 | 0ms ✅ | 0ms ✅ | 无变化 |
| TTS 完成 → 开始录音 | 800ms ⚠️ | 500ms ⚠️ | **减少 300ms** |

---

## 🎬 总结

**当前最大的问题：** 点击"发送"按钮后，音效播放延迟明显（500-800ms）

**根本原因：** 音效播放在 `handleSend()` 中，而 `handleSend()` 是在录音停止回调中延迟 500ms 后才调用的

**解决方案：** 将发送音效移到 `handleMicToggle()` 中，在停止录音之前立即播放

**次要问题：** WebSocket 连接延迟（800ms）导致实际录音启动较慢

**解决方案：** 测试并减少延迟时间到 500ms 或更少
