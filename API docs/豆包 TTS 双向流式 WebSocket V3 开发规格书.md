## 豆包 TTS 双向流式 WebSocket V3 开发规格书

### 1. 握手与连接参数 (Connection)

* **请求地址**: `wss://openspeech.bytedance.com/api/v3/tts/bidirection`
* **必需 Header**:
* `X-Api-App-Key`: 你的 APPID
* `X-Api-Access-Key`: 你的 Access Token
* `X-Api-Resource-Id`: `seed-tts-2.0`（大模型 2.0 字符版）
* `X-Api-Connect-Id`: 随机生成的 UUID（每个连接唯一）
* `X-Control-Require-Usage-Tokens-Return`: `*` (建议携带，用于返回计费字符数)

---

### 2. 二进制帧结构 (The Binary Protocol)

**所有整数使用大端序 (Big-Endian)**。每一帧由以下部分组成：

| 偏移 (Byte) | 字段名称 | 长度 | 说明 |
| --- | --- | --- | --- |
| 0 | `Header` | 1 byte | `0x11` (Version 1, Header size 4) |
| 1 | `Message Type & Flags` | 1 byte | 定义消息类型 (见下表) |
| 2 | `Serial & Compress` | 1 byte | `0x10` (JSON, 无压缩) 或 `0x00` (Raw, 无压缩) |
| 3 | `Reserved` | 1 byte | `0x00` |
| 4-7 | `Event Number` | 4 bytes | 仅当 Message Type Flags 包含 Event 时存在 |
| 8-11 | `Payload Size` | 4 bytes | 后续 Payload 的字节长度 |
| 12... | `Payload` | 变长 | JSON 字符串或原始音频二进制数据 |

**关键 Message Type 映射:**

* `0x14`: Full-client request (客户端发起的含 Event 的 JSON 请求)
* `0x94`: Full-server response (服务端返回的含 Event 的 JSON 响应)
* `0xB4`: Audio-only response (服务端返回的纯音频数据)
* `0xF0`: Error information (错误信息)

---

### 3. 会话状态机与 JSON 示例

#### 步骤 A: 开启会话 (StartSession)

连接建立后，必须先发送 `StartSession` 事件（Event Number: `111`）。

**Payload JSON 示例:**

```json
{
    "user": {
        "uid": "user_123456"
    },
    "event": {
        "namespace": "BidirectionalTTS"
    },
    "req_params": {
        "model": "seed-tts-2.0-expressive",
        "speaker": "音色ID",
        "audio_params": {
            "format": "pcm", 
            "sample_rate": 24000,
            "bit_rate": 128000,
            "speed_rate": 0,
            "emotion": "happy",
            "emotion_scale": 4
        }
    }
}

```

#### 步骤 B: 提交文本 (TaskRequest)

在收到 `SessionStarted` (Event 151) 响应后，开始流式提交文本（Event Number: `131`）。你可以根据 LLM 的输出节奏多次调用。

**Payload JSON 示例:**

```json
{
    "text": "这是第一段文本，我会接着发下一段。"
}

```

*注意：双向流式不支持 SSML 标签，直接传纯文本。*

#### 步骤 C: 结束会话 (FinishSession)

当 LLM 吐字完毕，必须告知服务端文本已结束（Event Number: `112`）。

**Payload JSON 示例:**

```json
{} // 传空 JSON 对象即可

```

#### 步骤 D: 服务端反馈

* **音频响应 (Event 132)**: 返回二进制音频。
* **字幕响应 (Event 133)**:
```json
{
    "text": "这是一段文本",
    "words": [
        { "word": "这是", "startTime": 0, "endTime": 200 },
        { "word": "一段", "startTime": 200, "endTime": 400 }
    ]
}

```


* **会话结束 (SessionFinished - Event 152)**: 收到此包代表该轮语音全部生成并下发完毕。

---

### 4. 异常处理与打断逻辑

* **打断 (CancelSession)**:
如果采访中用户突然说话，需立即发送 `CancelSession` (Event `113`)。收到 `SessionCanceled` 后，该 Session 销毁。若要重新开始，需重新执行 `StartSession`。
* **状态码**:
服务端返回的 `status_code` 如果不是 `20000000`，代表出错。例如 `40000001` 可能代表鉴权失败。

---

### 5. 给 Gemini 的开发建议 (你可以直接贴给他)

> 1. **Header 构造**: 严格按照 4 字节 Header + 4 字节 Event Number (可选) + 4 字节 Payload Size 的顺序构造二进制包。
> 2. **异步处理**: 使用异步双工模式，一个 Task 负责监听 WebSocket 读取（音频/字幕），主线程负责根据 LLM 进度推送 `TaskRequest`。
> 3. **连接复用**: 不要每次合成都断开 WebSocket。一轮采访结束后，发送 `FinishSession`，等待 `SessionFinished`；下一轮提问直接从 `StartSession` 开始。
> 4. **音频拼接**: 由于是流式返回 PCM，请确保前端播放器能够处理流式 Buffer 的无缝拼接，避免爆音。
> 
> 