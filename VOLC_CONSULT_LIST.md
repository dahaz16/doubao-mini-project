# 火山引擎 TTS V3 技术咨询列表 (Technical Consultation for Volcengine)

为了彻底解决“秒开”时的卡顿、静默和协议报错问题，请将以下技术细节发给火山引擎 AI 或技术支持，寻求官方标准的实现建议：

---

### 问题 1：关于连接复用与并发处理 (Connection & Concurrency)
**背景**：为了减少每句话 500ms 的握手延迟，我们尝试维护一个全局的 WebSocket 长连接。但在测试中发现，如果前方有多个 `GET /tts/stream` 请求同时进来，共用一个 Socket 发送 `StartSession`，火山引擎会返回 `Protocol Error (Type 15)`。
**咨询建议**：
- 火山 TTS V3 协议是否允许在同一个 WebSocket 连接上**串行（队列）**运行多个 Session？
- 如果允许，在发送下一个 `StartSession` 之前，是否必须严格等待前一个 Session 的 `SessionFinished (Event 152)`？
- 官方是否推荐在服务端维护一个 **Connection Pool**，还是建议“每次请求、独立连接、完后即断”？

### 问题 2：关于 HTTP 流式传输 (Mode B) 的缓冲区 (Buffering)
**背景**：我们目前在用 FastAPI 的 `StreamingResponse` 将 WebSocket 收到的音频包实时 push 给小程序。
**咨询建议**：
- 对于 `audio/mpeg` (MP3) 格式的流式返回，官方建议的**最小切片大小**是多少？
- 如果后端一收到火山的几个字节就立刻 `yield` 给前端，是否会触发前端播放器的缓冲保护机制导致停顿？
- 后端是否需要手动拼接几帧 MP3 数据再下发？

### 问题 3：关于文本切分与首包延迟 (Sentence Splitting)
**背景**：LLM 正在流式产生文本。我们通过标点符号 `。！？` 来切句送去 TTS。
**咨询建议**：
- 如果 LLM 输出非常慢，或者一句话特别长（比如 100 字没标点），官方有没有推荐的“强制冲刷 (Flush)”策略？
- 是否可以在不发送 `FinishSession` 的情况下，持续往一个 Session 里追加文本并获取音频？还是必须一句话对应一个 Session？

### 问题 4：关于微信小程序 `InnerAudioContext` 的兼容性
**背景**：小程序在播放 `/tts/stream?text=...` 这种动态流 URL 时，有时会从中间开始播放或无法识别时长。
**咨询建议**：
- 使用 HTTP Streaming 返回时，HTTP Response Header 中是否必须包含 `Content-Length`（流式下通常没有）或特定的 `Range` 支持？
- 对于分段音频，如何确保两句话之间的“无缝缝合”，避免播放器切换 URL 时的机械停顿感？

---

**当前现状总结：**
- **当前瓶颈**：建立连接太慢（~500ms），复用连接容易报错（Type 15），切句太快前端声音琐碎，切句太慢用户等待时间长。
- **目标**：实现首字出炉后 500ms 内听到声音，且播放过程不卡顿。
