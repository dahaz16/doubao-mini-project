双向流式websocket-V3-支持复刻/混音mix  
  
# 双向流式TTS API接口文档  
## 1 接口功能  
双向流式API为用户提供**文本转语音**能力，支持多语种、多方言，基于WebSocket协议实现流式调用，支持两种交互方式：  
1.  一包发送全部请求数据  
2.  边发数据边接收音频的流式交互  
  
### 1.1 最佳实践  
该接口可自动处理碎片化或过长文本，整理为长度合适的句子，核心优势是**平衡合成延迟与合成效果**。  
  
对接大文本模型时的建议：  
1.  直接将大模型的流式输出文本传入该接口，无需额外开发切句、攒句逻辑；单次调用该接口的合成效果，优于多次调用普通合成接口，语音更自然、情绪更饱满。  
2.  推荐采用**链接复用**的接入方式，流程如下：  
    - 发送 `startconnection` 建立WebSocket连接  
    - 收到 `ConnectionStarted` 即表示连接建立成功  
    - 发送 `startsession`，通过 `taskrequest` 传输文本，同时接收音频  
    - 无文本发送时，立即发送 `finish session`  
    - 若还有文本需要合成，**必须**等待收到 `SessionFinished` 后，重新发送 `startsession` 开启新一轮会话  
    - 若无需继续合成，发送 `finish connection` 断开链接  
  
**注意**：同一个WebSocket连接下支持多次会话，但**不支持同时并行多个会话**。  
  
## 2 接口说明  
### 2.1 请求（Request）  
#### 2.1.1 请求路径  
```  
wss://openspeech.bytedance.com/api/v3/tts/bidirection  
```  
  
#### 2.1.2 建连&鉴权  
在WebSocket建连的HTTP请求头（Request Header）中，需添加以下鉴权信息：  
  
| Key | 说明 | 是否必须 | Value示例 |  
|-----|------|----------|-----------|  
| X-Api-App-Key | 火山引擎控制台获取的APP ID，参考[控制台使用FAQ-Q1](/docs/6561/196768#q1：哪里可以获取到以下参数appid，cluster，token，authorization-type，secret-key-？) | 是 | 123456789 |  
| X-Api-Access-Key | 火山引擎控制台获取的Access Token，参考[控制台使用FAQ-Q1](/docs/6561/196768#q1：哪里可以获取到以下参数appid，cluster，token，authorization-type，secret-key-？) | 是 | your-access-key |  
| X-Api-Resource-Id | 调用服务的资源信息ID，不同模型对应不同取值：<br>1. 豆包语音合成模型1.0：<br>   - 字符版：seed-tts-1.0 / volc.service_type.10029<br>   - 并发版：seed-tts-1.0-concurr / volc.service_type.10048<br>2. 豆包语音合成模型2.0：<br>   - 字符版：seed-tts-2.0<br>3. 声音复刻：<br>   - 1.0字符版：seed-icl-1.0<br>   - 1.0并发版：seed-icl-1.0-concurr<br>   - 2.0字符版：seed-icl-2.0<br><br>**注意**：资源ID与对应模型的音色绑定，不可混用 | 是 | seed-tts-1.0 |  
| X-Api-Connect-Id | 追踪连接的标志ID，建议传递，便于排查问题；每个会话ID需唯一，请求失败重连时需重新生成 | 否 | 67ee89ba-7050-4c04-a3d7-ac61a63499b3 |  
| X-Control-Require-Usage-Tokens-Return | 用量数据返回控制标记，携带此字段时，`SessionFinish` 事件（152）会返回用量数据：<br>- 设置为`*`：返回所有已支持的用量数据<br>- 设置为具体标记（如`text_words`）：返回指定数据，多个标记用逗号分隔<br>当前支持：`text_words`（计费字符数） | 否 | text_words |  
  
**建连响应头**：握手成功后，服务端返回的Response Header包含以下字段  
| Key | 说明 | Value示例 |  
|-----|------|-----------|  
| X-Tt-Logid | 服务端生成的日志ID，建议打印留存，用于问题定位 | 202407261553070FACFE6D19421815D605 |  
  
#### 2.1.3 WebSocket二进制协议  
WebSocket采用二进制协议传输数据，协议结构由三部分组成：  
1.  **可变Header**：至少4字节，描述消息类型、序列化方式、压缩格式等  
2.  **Payload Size**：负载数据长度  
3.  **Payload**：具体的负载内容（文本、音频等）  
  
**协议说明**：协议中所有整数类型字段均采用**大端序**表示。  
  
##### 二进制帧结构  
| Byte | Left 4-bit | Right 4-bit | 说明 |  
|------|------------|-------------|------|  
| 0 - 左半部分 | Protocol version | - | 固定为`0b0001`（v1版本） |  
| 0 - 右半部分 | - | Header size (4x) | 固定为`0b0001`（Header长度为4字节） |  
| 1 | Message type | Message type specific flags | 消息类型及专属标识，详见下文 |  
| 2 - 左半部分 | Serialization method | - | 序列化方式：<br>`0b0000`=Raw（二进制音频数据）<br>`0b0001`=JSON（文本类消息） |  
| 2 - 右半部分 | - | Compression method | 压缩方式：<br>`0b0000`=无压缩<br>`0b0001`=gzip |  
| 3 | Reserved | Reserved | 保留位，固定填`0b0000 0000` |  
| 4~7 | Optional field | - | 可选字段，如event number，是否存在取决于Message type specific flags |  
| ... | Payload | - | 负载数据，可能是音频、文本或混合数据 |  
  
##### Message type & specific flags  
| Message type | 含义 | Message type specific flags | 是否包含Event number | 备注 |  
|--------------|------|-----------------------------|----------------------|------|  
| 0b0001 | Full-client request | 0b0100 | 是 | 完整请求体，用于初始化服务端session |  
| 0b1001 | Full-server response | 0b0100 | 是 | TTS响应，包含前端信息、文本音频混合数据（序列化方式为JSON） |  
| 0b1011 | Audio-only response | 0b0100 | 是 | 仅返回音频数据的响应 |  
| 0b1111 | Error information | None | 否 | 错误信息响应 |  
  
##### Payload请求参数  
**注意**：TTS服务参数仅在`StartSession`时生效，文本内容在`TaskRequest`时传输。  
  
| 字段 | 描述 | 是否必须 | 类型 | 默认值 |  
|------|------|----------|------|--------|  
| user | 用户信息 | 否 | object | - |  
| user.uid | 用户唯一标识 | 否 | string | - |  
| event | 请求事件类型 | 是 | number | - |  
| namespace | 请求方法 | 否 | string | BidirectionalTTS |  
| req_params.text | 输入文本，**不支持SSML** | 是 | string | - |  
| req_params.model | 模型版本，传`seed-tts-1.1`音质更佳、延迟更低；复刻场景下会放大训练音频特质，对训练音频质量要求更高 | 否 | string | - |  
| req_params.speaker | 发音人，取值参考[发音人列表](https://www.volcengine.com/docs/6561/1257544) | 是 | string | - |  
| req_params.audio_params | 音频参数，减少服务端解码耗时 | 是 | object | - |  
| req_params.audio_params.format | 音频编码格式，支持mp3/ogg_opus/pcm；传入wav不会报错，但流式场景会多次返回wav header，建议用pcm | 否 | string | mp3 |  
| req_params.audio_params.sample_rate | 音频采样率，可选值[8000,16000,22050,24000,32000,44100,48000] | 否 | number | 24000 |  
| req_params.audio_params.bit_rate | 音频比特率，默认范围64k~160k；设置`disable_default_bit_rate=true`可支持64k以下；MP3/ogg格式建议主动设置，默认8k音质损耗较大；wav格式比特率=采样率×位深度×声道数 | 否 | number | - |  
| req_params.audio_params.emotion | 音色情感，仅部分音色支持，取值参考[多情感音色列表](https://www.volcengine.com/docs/6561/1257544) | 否 | string | - |  
| req_params.audio_params.emotion_scale | 情感强度，范围1~5，需配合emotion使用；强度为非线性增长，过高值提升效果不明显 | 否 | number | 4 |  
| req_params.audio_params.speech_rate | 语速，范围[-50,100]；100=2.0倍速，-50=0.5倍速 | 否 | number | 0 |  
| req_params.audio_params.loudness_rate | 音量，范围[-50,100]；100=2.0倍音量，-50=0.5倍音量（mix音色不支持） | 否 | number | 0 |  
| req_params.audio_params.enable_timestamp | 开启句级/字级时间戳，**仅TTS1.0支持** | 否 | bool | false |  
| req_params.additions | 用户自定义参数 | 否 | json string | - |  
| req_params.additions.silence_duration | 句尾静音时长，范围0~30000ms（仅对文本末尾生效） | 否 | number | 0 |  
| req_params.additions.enable_language_detector | 自动识别语种 | 否 | bool | false |  
| req_params.additions.disable_markdown_filter | 是否过滤Markdown语法：true=过滤（如`**你好**`读为“你好”）；false=不过滤（读为“星星你好星星”） | 否 | bool | false |  
| req_params.additions.disable_emoji_filter | 是否过滤Emoji，建议配合时间戳使用 | 否 | bool | false |  
| req_params.additions.mute_cut_remain_ms | 静音保留时长，需配合`mute_cut_threshold`使用；参数值均为string类型；MP3句首会有100ms内静音无法消除 | 否 | string | - |  
| req_params.additions.enable_latex_tn | 是否播报LaTeX公式，需设置`disable_markdown_filter=true` | 否 | bool | false |  
| req_params.additions.max_length_to_filter_parenthesis | 括号内容过滤阈值：0=不过滤，100=过滤 | 否 | int | 100 |  
| req_params.additions.explicit_language | 明确合成语种，不同场景支持范围不同（详见原文档） | 否 | string | - |  
| req_params.additions.context_language | 参考语种，影响西欧语种合成效果 | 否 | string | - |  
| req_params.additions.unsupported_char_ratio_thresh | 不支持字符比例阈值，超过则返回错误；范围0~1.0 | 否 | float | 0.3 |  
| req_params.additions.aigc_watermark | 是否在音频结尾添加节奏标识水印 | 否 | bool | false |  
| req_params.additions.aigc_metadata | 音频元数据隐式水印，支持mp3/wav/ogg_opus | 否 | object | - |  
| req_params.additions.cache_config | 缓存配置，相同文本合成可读取缓存，提升速率；缓存保留1小时 | 否 | object | - |  
| req_params.additions.post_process | 后处理配置，如音调调整 | 否 | object | - |  
| req_params.additions.context_texts | 合成辅助信息，用于对话式合成优化情感，**仅TTS2.0支持**；仅列表第一个值有效，文本不计费 | 否 | string list | null |  
| req_params.additions.section_id | 历史会话ID，辅助当前合成，**仅TTS2.0支持**；有效期最长30轮/10分钟 | 否 | string | "" |  
| req_params.additions.use_tag_parser | 是否开启COT解析，调整语速/情感；**仅声音复刻2.0音色支持**；单句文本（含标签）长度建议<64字符 | 否 | bool | false |  
| req_params.mix_speaker | 混音参数，**仅TTS1.0支持** | 否 | object | - |  
| req_params.mix_speaker.speakers | 混音音色列表，最多支持3个；因子和为1；复刻音色需用icl_开头的speakerid | 否 | list | null |  
| req_params.mix_speaker.speakers[i].source_speaker | 混音源音色名 | 否 | string | "" |  
| req_params.mix_speaker.speakers[i].mix_factor | 混音影响因子 | 否 | float | 0 |  
  
###### 请求参数示例  
1.  **单音色请求**  
    ```json  
    {  
        "user": {  
            "uid": "12345"  
        },  
        "event": 100,  
        "req_params": {  
            "text": "明朝开国皇帝朱元璋也称这本书为万物之根",  
            "speaker": "zh_female_shuangkuaisisi_moon_bigtts",  
            "audio_params": {  
                "format": "mp3",  
                "sample_rate": 24000  
            }  
        }  
    }  
    ```  
  
2.  **混音请求**  
    ```json  
    {  
        "user": {  
            "uid": "12345"  
        },  
        "req_params": {  
            "text": "明朝开国皇帝朱元璋也称这本书为万物之根",  
            "speaker": "custom_mix_bigtts",  
            "audio_params": {  
                "format": "mp3",  
                "sample_rate": 24000  
            },  
            "mix_speaker": {  
                "speakers": [  
                    {  
                        "source_speaker": "zh_male_bvlazysheep",  
                        "mix_factor": 0.3  
                    },  
                    {  
                        "source_speaker": "BV120_streaming",  
                        "mix_factor": 0.3  
                    },  
                    {  
                        "source_speaker": "zh_male_ahu_conversation_wvae_bigtts",  
                        "mix_factor": 0.4  
                    }  
                ]  
            }  
        }  
    }  
    ```  
  
### 2.2 响应（Response）  
#### 2.2.1 建连响应  
建连阶段通过HTTP状态码判断结果：  
- 成功：状态码 `200`  
- 失败：状态码非`200`，响应Body中包含错误原因  
  
#### 2.2.2 WebSocket传输响应  
WebSocket响应分为两种类型：  
1.  **文本帧**：用于反馈异常错误信息  
2.  **二进制帧**：用于结构化返回正常响应和常规错误信息  
  
##### 正常响应帧结构  
与请求二进制帧结构一致，具体参考 **2.1.3 二进制帧结构** 章节。  
  
###### Payload响应参数  
| 字段 | 描述 | 类型 | 默认值 |  
|------|------|------|--------|  
| data | 返回的二进制数据包（音频数据） | []byte | - |  
| event | 返回的事件类型 | number | - |  
| res_params.text | 经分句后的文本内容 | string | - |  
  
##### 错误响应帧结构  
| Byte | Left 4-bit | Right 4-bit | 说明 |  
|------|------------|-------------|------|  
| 0 - 左半部分 | Protocol version | - | 固定为`0b0001` |  
| 0 - 右半部分 | - | Header size (4x) | 固定为`0b0001` |  
| 1 | Message type | Message type specific flags | 固定为`0b11110000` |  
| 2 - 左半部分 | Serialization method | - | 固定为`0b0001`（JSON格式） |  
| 2 - 右半部分 | - | Compression method | 固定为`0b0000`（无压缩） |  
| 3 | Reserved | Reserved | 固定为`0b0000 0000` |  
| 4~7 | Error code | - | 错误码 |  
| ... | Payload | - | 错误消息对象（JSON格式） |  
  
### 2.3 Event定义  
Event是上下行数据帧的必要字段，用于定义请求过程的状态转移，具体如下：  
  
| Event code | 含义 | 事件类型 | 应用阶段：上行/下行 |  
|------------|------|----------|--------------------|  
| 1 | StartConnection：创建WebSocket连接 | Connect类 | 上行 |  
| 2 | FinishConnection：结束WebSocket连接 | Connect类 | 上行 |  
| 50 | ConnectionStarted：连接建立成功 | Connect类 | 下行 |  
| 51 | ConnectionFailed：连接建立失败 | Connect类 | 下行 |  
| 52 | ConnectionFinished：连接结束成功 | Connect类 | 下行 |  
| 100 | StartSession：创建会话 | Session类 | 上行 |  
| 101 | CancelSession：取消会话 | Session类 | 上行 |  
| 102 | FinishSession：声明结束会话 | Session类 | 上行 |  
| 150 | SessionStarted：会话创建成功 | Session类 | 下行 |  
| 151 | SessionCanceled：会话已取消 | Session类 | 下行 |  
| 152 | SessionFinished：会话已结束 | Session类 | 下行 |  
| 153 | SessionFailed：会话创建失败 | Session类 | 下行 |  
| 200 | TaskRequest：传输请求文本 | 数据类 | 上行 |  
| 350 | TTSSentenceStart：TTS开始返回句子 | 数据类 | 下行 |  
| 351 | TTSSentenceEnd：TTS结束返回句子 | 数据类 | 下行 |  
| 352 | TTSResponse：TTS返回音频数据 | 数据类 | 下行 |  
  
## 3 交互示例  
![交互流程图](https://p9-arcosite.byteimg.com/tos-cn-i-goo7wpa0wc/55ef2efccd7c4baa8a2b8ba77dd0f444~tplv-goo7wpa0wc-image.image =3632x)  
  
### 3.1 CancelSession注意事项  
1.  `CancelSession` 用于客户端主动终止当前会话，释放服务端资源  
2.  发送时机：收到 `SessionStarted` 后，发送 `FinishSession` 之前  
3.  收到 `SessionCanceled` 后，若需继续合成，需重新发送 `StartSession` 创建新会话  
  
### 3.2 各类事件包结构  
#### 3.2.1 Connection类  
1.  **StartConnection包（RequestMeta）**  
    | Byte | Left 4-bit | Right 4-bit | 备注 |  
    |------|------------|-------------|------|  
    | 0 | 0001 | 0001 | v1版本，4字节Header |  
    | 1 | 0001 | 0100 | Full-client request，携带event number |  
    | 2 | 0001 | 0000 | JSON序列化，无压缩 |  
    | 3 | 0000 | 0000 | 保留位 |  
    | 4~7 | int32(Event_StartConnection) | - | 事件类型值 |  
    | 8~11 | uint32(2) | - | Payload长度 |  
    | 12~93 | {} | - | 空JSON，扩展保留 |  
  
2.  **FinishConnection包（RequestMeta）**：结构与StartConnection一致，仅事件类型为`Event_FinishConnection`  
  
3.  **ConnectionStarted包（ResponseMeta）**  
    | Byte | Left 4-bit | Right 4-bit | 备注 |  
    |------|------------|-------------|------|  
    | 0 | 0001 | 0001 | v1版本，4字节Header |  
    | 1 | 1001 | 0100 | Full-server response，携带event number |  
    | 2 | 0001 | 0000 | JSON序列化，无压缩 |  
    | 3 | 0000 | 0000 | 保留位 |  
    | 4~7 | int32(Event_ConnectionStarted) | - | 事件类型值 |  
    | 8~11 | uint32(7) | - | Connection ID长度 |  
    | 12~18 | bxnweiu | - | Connection ID示例 |  
    | 19~22 | uint32(2) | - | Payload长度 |  
    | 23~24 | {} | - | 空JSON，扩展保留 |  
  
4.  **ConnectionFailed包（ResponseMeta）**：Payload为错误信息JSON，包含`status_code`和`message`字段  
  
#### 3.2.2 Session类  
以`StartSession`包为例，其他Session类事件包结构类似，仅事件类型和Payload内容不同：  
| Byte | Left 4-bit | Right 4-bit | 备注 |  
|------|------------|-------------|------|  
| 0 | 0001 | 0001 | v1版本，4字节Header |  
| 1 | 0001 | 0100 | Full-client request，携带event number |  
| 2 | 0001 | 0000 | JSON序列化，无压缩 |  
| 3 | 0000 | 0000 | 保留位 |  
| 4~7 | int32(Event_StartSession) | - | 事件类型值 |  
| 8~11 | uint32(12) | - | Session ID长度 |  
| 12~23 | nxckjoejnkegf | - | Session ID示例 |  
| 24~27 | uint32(...) | - | TTS参数Payload长度 |  
| 28~... | {user:..., req_params:...} | - | TTS会话参数JSON |  
  
**注意**：客户端必须填写`session_id`，不可留空。  
  
#### 3.2.3 数据类  
1.  **音频数据请求包（TaskRequest事件）**：序列化方式为Raw，Payload为二进制音频数据  
2.  **文本数据请求包（TaskRequest事件）**：序列化方式为JSON，Payload为文本参数JSON  
  
## 4 错误码  
### 4.1 新框架错误码  
```json  
{  
    "CodeOK": 20000000,        // 成功  
    "CodeClientError": 45000000,  // 客户端通用错误  
    "CodeServerError": 55000000,  // 服务端通用错误  
    "CodeSessionError": 55000001, // 服务端会话错误  
    "CodeInvalidReqError": 45000001 // 客户端请求参数错误  
}  
```  
  
## 5 调用示例  
支持Python、Java、Go、C#、TypeScript等多种语言，以下为通用步骤，具体语言细节参考对应示例代码：  
  
### 5.1 前提条件  
获取以下信息：  
1.  `<appid>`：火山引擎控制台获取，参考[控制台FAQ-Q1](https://www.volcengine.com/docs/6561/196768#q1%EF%BC%9A%E5%93%AA%E9%87%8C%E5%8F%AF%E4%BB%A5%E8%8E%B7%E5%8F%96%E5%88%B0%E4%BB%A5%E4%B8%8B%E5%8F%82%E6%95%B0appid%EF%BC%8Ccluster%EF%BC%8Ctoken%EF%BC%8Cauthorization-type%EF%BC%8Csecret-key-%EF%BC%9F)  
2.  `<access_token>`：火山引擎控制台获取  
3.  `<voice_type>`：音色ID，参考[大模型音色列表](https://www.volcengine.com/docs/6561/1257544)  
  
### 5.2 环境准备  
1.  安装对应语言的版本（如Python 3.9+、Java 21+、Go 1.21+等）  
2.  下载对应语言的示例代码包  
3.  解压并安装依赖  
  
### 5.3 发起调用  
替换命令行中的`<appid>`、`<access_token>`、`<voice_type>`参数，执行调用命令，示例（Python）：  
```bash  
python3 examples/volcengine/bidirection.py --appid <appid> --access_token <access_token> --voice_type <voice_type> --text "你好，我是火山引擎的语音合成服务"  
```  
