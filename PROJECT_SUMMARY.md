# 项目开发总结报告 (Project Summary & Post-Mortem)

本项目旨在构建一个基于微信小程序、FastAPI 后端以及火山引擎 AI 服务的实时语音交互回忆录系统。

## 1. 已实现功能 (Features Implemented)

### 核心交互
- **语音输入 (ASR)**：点击“讲述”开始采集 PCM 音频，实时流式发送至后端进行 ASR 识别并在前端展示实时字幕。
- **对话引擎 (LLM)**：后端集成豆包（Doubao）大模型，支持流式文本返回，引导用户进行回忆录创作。
- **语音播放 (TTS)**：后端将 LLM 返回的文本实时切分，通过火山引擎 TTS V3 协议生成语音流，并使用 HTTP Streaming (Mode B) 技术回传给小程序播放。
- **UI/UX 优化**：将原本的“长按说话”改为更稳定的“点击录音-点击停止-点击发送”模式，解决了交互死锁问题。

### 架构优势
- **Mode B HTTP 流式传输**：弃用了不稳定的 WebSocket 直接回传 PCM 方案，改用标准 HTTP 流，提升播放器兼容性与稳定性。
- **全局连接池 (Connection Pool)**：后端维护 TTS 长连接，消灭了每句话之间 500ms+ 的 TCP/SSL 握手延迟。
- **句子级并行分发**：LLM 边出字，后端边切句播放，实现真正的流式对话感。

---

## 2. 项目过程中踩过的“坑” (The Pits & Pitfalls)

### 后端技术坑
1.  **火山 ASR V2 鉴权陷阱**：火山 ASR 2.0 协议要求在 Header 中同时包含 `X-Api-App-Key` 和 `X-Api-Access-Key`，且 `ResourceID` 必须根据计费模式选择（如 `volc.seedasr.sauc.duration`）。初期因参考了 1.0 文档导致频繁 401/403。
2.  **TTS V3 二进制协议复杂性**：TTS V3 采用自定义二进制封包（Header + 4字节Event + Payload）。在解析音频包和事件包（SessionFinished）时，字节偏移量计算极易出错，导致流提前关闭或数据错乱。
3.  **websockets 15.0 API 变更**：最新的 `websockets` 库移出了 `.open` 和 `.closed` 属性，改用 `.state` 枚举。这导致在连接复用逻辑中出现 `AttributeError`，造成 TTS 服务表面成功实际无输出。（*已修复*）
4.  **SSL 证书验证**：在本地开发环境下，Python 直接连接火山服务器常因 SSL 解析报错。最终通过 `ssl._create_unverified_context()` 绕过。

### 前端/真机坑
1.  **微信播放器 src 切换延迟**：小程序 `InnerAudioContext` 在切换 `src` 时会有内部缓冲开销。我们通过后端提前下发 URL 预加载来缓解。
2.  **双重播放指令漏洞**：由于前端监听机制或状态机逻辑，初期会出现一句话请求两次 TTS 的情况，导致声音重叠（“刺啦”声）。增加了 `currentUrl` 锁后解决。
3.  **开发者工具与真机差异**：Mac 开发者工具采集的音频位深、采样率与手机真机有细微差别，需在后端进行 PCM 严格对齐（16k/16bit/Mono）。

---

## 3. 最终能够跑通的最佳方式 (The Golden Path)

### 架构结论：**流式分段 + HTTP 模式 B + 全局长连接**

1.  **后端模式**：
    *   不要在每次请求 TTS 时都 `connect()`。必须使用 **FastAPI Lifespan** 维护一个全局的 `VolcTTSClient` 长连接。
    *   使用 `StreamingResponse` 返回 `audio/mpeg` (MP3格式)，这比 PCM 在网络波动下表现更稳健。
2.  **前端模式**：
    *   维护一个 `audioQueue`。
    *   每当收到后端的 `play_audio` 信号，立即 push 到队列。
    *   通过 `onEnded` 事件驱动递归播放，不要手动干预播放器停止。
3.  **文本切分策略**：
    *   后端使用正则表达式 `[。！？\.\!\?]` 实时监测 LLM 输出，一旦发现标点符号立即截断送去 TTS，保证第一句话的响应速度控制在 300ms-500ms 内。

---

## 4. 当前状态与建议 (Next Steps)

*   **当前 TTFB 测试结果**：服务器到首字节响应时间约 **333ms**。
*   **建议建议**：如果觉得首句不够快，可以在 System Prompt 中要求 AI “第一句话尽量简短且直接”，从而让 TTS 更快触发。
