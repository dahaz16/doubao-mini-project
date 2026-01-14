<span id="d7a28c45"></span>
# 1 接口功能
单向流式API为用户提供文本转语音的能力，支持多语种、多方言，同时支持http协议流式输出。
<span id="27edde0a"></span>
## 1.1最佳实践

* 客户端读取服务端流式返回的json数据，从中取出对应的音频数据；
* 音频数据返回的是base64格式，需要解析后拼接到字节数组即可组装音频进行播放；
* 可以使用对应编程语言的连接复用组件，避免重复建立tcp连接（火山服务端keep-alive时间为1分钟），例如python的session组件：

```JSON
session = requests.Session()
response = session.post(url, headers=headers, json=payload, stream=True)
```


<span id="14358605"></span>
# 2 接口说明
<span id="5495b4ca"></span>
## 2.1 请求Request
<span id="f38e3780"></span>
### 请求路径

* 服务对应的请求路径：`https://openspeech.bytedance.com/api/v3/tts/unidirectional`

<span id="1b6e0bd5"></span>
### Request Headers

| | | | | \
|Key |说明 |是否必须 |Value示例 |
|---|---|---|---|
| | | | | \
|X-Api-App-Id |\
| |使用火山引擎控制台获取的APP ID，可参考 [控制台使用FAQ-Q1](https://www.volcengine.com/docs/6561/196768#q1%EF%BC%9A%E5%93%AA%E9%87%8C%E5%8F%AF%E4%BB%A5%E8%8E%B7%E5%8F%96%E5%88%B0%E4%BB%A5%E4%B8%8B%E5%8F%82%E6%95%B0appid%EF%BC%8Ccluster%EF%BC%8Ctoken%EF%BC%8Cauthorization-type%EF%BC%8Csecret-key-%EF%BC%9F) |是 |\
| | | |123456789 |\
| | | | |
| | | | | \
|X-Api-Access-Key |\
| |使用火山引擎控制台获取的Access Token，可参考 [控制台使用FAQ-Q1](https://www.volcengine.com/docs/6561/196768#q1%EF%BC%9A%E5%93%AA%E9%87%8C%E5%8F%AF%E4%BB%A5%E8%8E%B7%E5%8F%96%E5%88%B0%E4%BB%A5%E4%B8%8B%E5%8F%82%E6%95%B0appid%EF%BC%8Ccluster%EF%BC%8Ctoken%EF%BC%8Cauthorization-type%EF%BC%8Csecret-key-%EF%BC%9F) |是 |\
| | | |your-access-key |\
| | | | |
| | | | | \
|X-Api-Resource-Id |\
| |表示调用服务的资源信息 ID |\
| | |\
| |* 豆包语音合成模型1.0： |\
| |   * seed-tts-1.0 或者 volc.service_type.10029（字符版） |\
| |   * seed-tts-1.0-concurr 或者 volc.service_type.10048（并发版） |\
| |* 豆包语音合成模型2.0:   |\
| |   * seed-tts-2.0 (字符版) |\
| |* 声音复刻： |\
| |   * seed-icl-1.0（声音复刻1.0字符版） |\
| |   * seed-icl-1.0-concurr（声音复刻1.0并发版） |\
| |   * seed-icl-2.0 (声音复刻2.0字符版) |\
| | |\
| |**注意：** |\
| | |\
| |* "豆包语音合成模型1.0"的资源信息ID仅适用于["豆包语音合成模型1.0"的音色](https://www.volcengine.com/docs/6561/1257544) |\
| |* "豆包语音合成模型2.0"的资源信息ID仅适用于["豆包语音合成模型2.0"的音色](https://www.volcengine.com/docs/6561/1257544) |是 |\
| | | |* 豆包语音合成模型1.0： |\
| | | |   * seed-tts-1.0  |\
| | | |   * seed-tts-1.0-concurr |\
| | | |* 豆包语音合成模型2.0:   |\
| | | |   * seed-tts-2.0  |\
| | | |* 声音复刻： |\
| | | |   * seed-icl-1.0（声音复刻1.0字符版） |\
| | | |   * seed-icl-1.0-concurr（声音复刻1.0并发版） |\
| | | |   * seed-icl-2.0 (声音复刻2.0字符版) |
| | | | | \
|X-Api-Request-Id |标识客户端请求ID，uuid随机字符串 |否 |67ee89ba-7050-4c04-a3d7-ac61a63499b3 |
| | | | | \
|X-Control-Require-Usage-Tokens-Return |请求消耗的用量返回控制标记。当携带此字段，在合成音频结束时的返回数据中会多一个usage的JSON Object字段，其中包含了所需的用量数据。 |否 |* 设置为*，表示返回已支持的用量数据。 |\
| | | |* 也设置为具体的用量数据标记，如text_words；多个用逗号分隔 |\
| | | |* 当前已支持的用量数据 |\
| | | |   * text_words，表示计费字符数 |


<span id="bf142291"></span>
### Response Headers

| | | | \
|Key |说明 |Value示例 |
|---|---|---|
| | | | \
|X-Tt-Logid |服务端返回的 logid，建议用户获取和打印方便定位问题 |2025041513355271DF5CF1A0AE0508E78C |

<span id="1aa30415"></span>
## 2.2 请求Body

| | | | | | \
|字段 |描述 |是否必须 |类型 |默认值 |
|---|---|---|---|---|
| | | | | | \
|user |用户信息 | | | |
| | | | | | \
|user.uid |用户uid | | | |
| | | | | | \
|namespace |请求方法 | |string |BidirectionalTTS |
| | | | | | \
|req_params.text |输入文本 | |string | |
| | | | | | \
|req_params.model |\
| |模型版本，传`seed-tts-1.1`较默认版本音质有提升，并且延时更优，不传为默认效果。 |\
| |注：若使用1.1模型效果，在复刻场景中会放大训练音频prompt特质，因此对prompt的要求更高，使用高质量的训练音频，可以获得更优的音质效果。 |否 |string |\
| | | | |—— |
| | | | | | \
|req_params.ssml |* 当文本格式是ssml时，需要将文本赋值为ssml，此时文本处理的优先级高于text。ssml和text字段，至少有一个不为空 |\
| |* ["豆包语音合成模型2.0"的音色](https://www.volcengine.com/docs/6561/1257544) 暂不支持 |\
| |* 豆包声音复刻模型2.0（icl 2.0）的音色暂不支持 | |string | |
| | | | | | \
|req_params.speaker |发音人，具体见[发音人列表](https://www.volcengine.com/docs/6561/1257544) |√ |string | |
| | | | | | \
|req_params.audio_params |音频参数，便于服务节省音频解码耗时 |√ |object | |
| | | | | | \
|req_params.audio_params.format |音频编码格式，mp3/ogg_opus/pcm。<span style="background-color: rgba(255,246,122, 0.8)">接口传入wav并不会报错，在流式场景下传入wav会多次返回wav header，这种场景建议使用pcm。</span> | |string |mp3 |
| | | | | | \
|req_params.audio_params.sample_rate |音频采样率，可选值 [8000,16000,22050,24000,32000,44100,48000] | |number |24000 |
| | | | | | \
|req_params.audio_params.bit_rate |音频比特率，可传16000、32000等。 |\
| |bit_rate默认设置范围为64k～160k，传了disable_default_bit_rate为true后可以设置到64k以下 |\
| |GoLang示例：`additions = fmt.Sprintf("{"disable_default_bit_rate":true}")` |\
| |**注：​**bit_rate只针对MP3格式，wav计算比特率跟pcm一样是 比特率 (bps) = 采样率 × 位深度 × 声道数 |\
| |目前大模型TTS只能改采样率，所以对于wav格式来说只能通过改采样率来变更音频的比特率 | |number | |
| | | | | | \
|req_params.audio_params.emotion |设置音色的情感。示例："emotion": "angry" |\
| |注：当前仅部分音色支持设置情感，且不同音色支持的情感范围存在不同。 |\
| |详见：[大模型语音合成API-音色列表-多情感音色](https://www.volcengine.com/docs/6561/1257544) | |string | |
| | | | | | \
|req_params.audio_params.emotion_scale |调用emotion设置情感参数后可使用emotion_scale进一步设置情绪值，范围1~5，不设置时默认值为4。 |\
| |注：理论上情绪值越大，情感越明显。但情绪值1~5实际为非线性增长，可能存在超过某个值后，情绪增加不明显，例如设置3和5时情绪值可能接近。 | |number |4 |
| | | | | | \
|req_params.audio_params.speech_rate |语速，取值范围[-50,100]，100代表2.0倍速，-50代表0.5倍数 | |number |0 |
| | | | | | \
|req_params.audio_params.loudness_rate |音量，取值范围[-50,100]，100代表2.0倍音量，-50代表0.5倍音量（mix音色暂不支持） | |number |0 |
| | | | | | \
|req_params.audio_params.enable_timestamp |\
|([仅TTS1.0支持](https://www.volcengine.com/docs/6561/1257544)) |设置 "enable_timestamp": true 返回句级别字的时间戳（默认为 flase，参数传入 true 即表示启用） |\
| |注意： |\
| | |\
| |1. 该字段仅适用于["豆包语音合成模型1.0"的音色](https://www.volcengine.com/docs/6561/1257544) | |bool |false |
| | | | | | \
|req_params.additions |用户自定义参数 | |jsonstring | |
| | | | | | \
|req_params.additions.silence_duration |设置该参数可在句尾增加静音时长，范围0~30000ms。（注：增加的句尾静音主要针对传入文本最后的句尾，而非每句话的句尾） | |number |0 |
| | | | | | \
|req_params.additions.enable_language_detector |自动识别语种 | |bool |false |
| | | | | | \
|req_params.additions.disable_markdown_filter |是否开启markdown解析过滤， |\
| |为true时，解析并过滤markdown语法，例如，`**你好**`，会读为“你好”， |\
| |为false时，不解析不过滤，例如，`**你好**`，会读为“星星‘你好’星星” | |bool |false |
| | | | | | \
|req_params.additions.disable_emoji_filter |开启emoji表情在文本中不过滤显示，默认为false，建议搭配时间戳参数一起使用。 |\
| |GoLang示例：`additions = fmt.Sprintf("{"disable_emoji_filter":true}")` | |bool |false |
| | | | | | \
|req_params.additions.mute_cut_remain_ms |该参数需配合mute_cut_threshold参数一起使用，其中： |\
| |"mute_cut_threshold": "400", // 静音判断的阈值（音量小于该值时判定为静音） |\
| |"mute_cut_remain_ms": "50", // 需要保留的静音长度 |\
| |注：参数和value都为string格式 |\
| |Golang示例：`additions = fmt.Sprintf("{"mute_cut_threshold":"400", "mute_cut_remain_ms": "1"}")` |\
| |**特别提醒：** |\
| | |\
| |* 因MP3格式的特殊性，句首始终会存在100ms内的静音无法消除，WAV格式的音频句首静音可全部消除，建议依照自身业务需求综合判断选择 | |string | |
| | | | | | \
|req_params.additions.enable_latex_tn |是否可以播报latex公式，需将disable_markdown_filter设为true | |bool |false |
| | | | | | \
|req_params.additions.latex_parser |是否使用lid 能力播报latex公式，相较于latex_tn 效果更好； |\
| |值为“v2”时支持lid能力解析公式，值为“”时不支持lid； |\
| |需同时将disable_markdown_filter设为true； | |string | |
| | | | | | \
|req_params.additions.max_length_to_filter_parenthesis |是否过滤括号内的部分，0为不过滤，100为过滤 | |int |100 |
| | | | | | \
|req_params.additions.explicit_language（明确语种） |仅读指定语种的文本 |\
| |**精品音色和 声音复刻ICL1.0场景：** |\
| | |\
| |* 不给定参数，正常中英混 |\
| |* `crosslingual` 启用多语种前端（包含`zh/en/ja/es-ms/id/pt-br`） |\
| |* `zh-cn` 中文为主，支持中英混  |\
| |* `en` 仅英文 |\
| |* `ja` 仅日文 |\
| |* `es-mx` 仅墨西 |\
| |* `id` 仅印尼 |\
| |* `pt-br` 仅巴葡 |\
| | |\
| |**DIT 声音复刻场景：** |\
| |当音色是使用model_type=2训练的，即采用dit标准版效果时，建议指定明确语种，目前支持： |\
| | |\
| |* 不给定参数，启用多语种前端`zh,en,ja,es-mx,id,pt-br,de,fr` |\
| |* `zh,en,ja,es-mx,id,pt-br,de,fr` 启用多语种前端 |\
| |* `zh-cn` 中文为主，支持中英混  |\
| |* `en` 仅英文 |\
| |* `ja` 仅日文 |\
| |* `es-mx` 仅墨西 |\
| |* `id` 仅印尼 |\
| |* `pt-br` 仅巴葡 |\
| |* `de` 仅德语 |\
| |* `fr` 仅法语 |\
| | |\
| |当音色是使用model_type=3训练的，即采用dit还原版效果时，必须指定明确语种，目前支持： |\
| | |\
| |* 不给定参数，正常中英混 |\
| |* `zh-cn` 中文为主，支持中英混  |\
| |* `en` 仅英文 |\
| | |\
| |**声音复刻 ICL2.0场景：** |\
| |当音色是使用model_type=4训练的 |\
| | |\
| |* 不给定参数，正常中英混 |\
| |* `zh-cn` 中文为主，支持中英混  |\
| |* `en` 仅英文 |\
| | |\
| |GoLang示例：`additions = fmt.Sprintf("{"explicit_language": "zh"}")` | |string | |
| | | | | | \
|req_params.additions.context_language（参考语种） |给模型提供参考的语种 |\
| | |\
| |* 不给定 西欧语种采用英语 |\
| |* id 西欧语种采用印尼 |\
| |* es 西欧语种采用墨西 |\
| |* pt 西欧语种采用巴葡 | |string | |
| | | | | | \
|req_params.additions.unsupported_char_ratio_thresh |默认: 0.3，最大值: 1.0 |\
| |检测出不支持合成的文本超过设置的比例，则会返回错误。 | |float |0.3 |
| | | | | | \
|req_params.additions.aigc_watermark |默认：false |\
| |是否在合成结尾增加音频节奏标识 | |bool |false |
| | | | | | \
|req_params.additions.aigc_metadata （meta 水印） |在合成音频 header加入元数据隐式表示，支持 mp3/wav/ogg_opus | |object | |
| | | | | | \
|req_params.additions.aigc_metadata.enable |是否启用隐式水印 | |bool |false |
| | | | | | \
|req_params.additions.aigc_metadata.content_producer |合成服务提供者的名称或编码 | |string |"" |
| | | | | | \
|req_params.additions.aigc_metadata.produce_id |内容制作编号 | |string |"" |
| | | | | | \
|req_params.additions.aigc_metadata.content_propagator |内容传播服务提供者的名称或编码 | |string |"" |
| | | | | | \
|req_params.additions.aigc_metadata.propagate_id |内容传播编号 | |string |"" |
| | | | | | \
|req_params.additions.cache_config（缓存相关参数） |开启缓存，开启后合成**相同文本**时，服务会直接读取缓存返回上一次合成该文本的音频，可明显加快相同文本的合成速率，缓存数据保留时间1小时。 |\
| |（通过缓存返回的数据不会附带时间戳） |\
| |Golang示例：`additions = fmt.Sprintf("{"disable_default_bit_rate":true, "cache_config": {"text_type": 1,"use_cache": true}}")` | |object | |
| | | | | | \
|req_params.additions.cache_config.text_type（缓存相关参数） |和use_cache参数一起使用，需要开启缓存时传1 | |int |1 |
| | | | | | \
|req_params.additions.cache_config.use_cache（缓存相关参数） |和text_type参数一起使用，需要开启缓存时传true | |bool |true |
| | | | | | \
|req_params.additions.post_process |后处理配置 |\
| |Golang示例：`additions = fmt.Sprintf("{"post_process":{"pitch":12}}")` | |object | |
| | | | | | \
|req_params.additions.post_process.pitch |音调取值范围是[-12,12] | |int |0 |
| | | | | | \
|req_params.additions.context_texts |\
|([仅TTS2.0支持](https://www.volcengine.com/docs/6561/1257544)) |语音合成的辅助信息，用于模型对话式合成，能更好的体现语音情感； |\
| |可以探索，比如常见示例有以下几种： |\
| | |\
| |1. 语速调整 |\
| |   1. 比如：context_texts: ["你可以说慢一点吗？"] |\
| |2. 情绪/语气调整 |\
| |   1. 比如：context_texts=["你可以用特别特别痛心的语气说话吗?"] |\
| |   2. 比如：context_texts=["嗯，你的语气再欢乐一点"] |\
| |3. 音量调整 |\
| |   1. 比如：context_texts=["你嗓门再小点。"] |\
| |4. 音感调整 |\
| |   1. 比如：context_texts=["你能用骄傲的语气来说话吗？"] |\
| | |\
| |注意： |\
| | |\
| |1. 该字段仅适用于["豆包语音合成模型2.0"的音色](https://www.volcengine.com/docs/6561/1257544) |\
| |2. 当前字符串列表只第一个值有效 |\
| |3. 该字段文本不参与计费 | |string list |null |
| | | | | | \
|[]req_params.mix_speaker |混音参数结构 |\
| |注意： |\
| | |\
| |1. 该字段仅适用于["豆包语音合成模型1.0"的音色](https://www.volcengine.com/docs/6561/1257544) | |object | |
| | | | | | \
|req_params.mix_speaker.speakers |混音音色名以及影响因子列表 |\
| | |\
| |1. 最多支持3个音色混音 |\
| |2. 混音影响因子和必须=1 |\
| |3. 使用复刻音色时，需要使用查询接口获取的icl_的speakerid，而非S_开头的speakerid |\
| |4. 音色风格差异较大的两个音色（如男女混），以0.5-0.5同等比例混合时，可能出现偶发跳变，建议尽量避免 |\
| | |\
| |注意：使用Mix能力时，req_params.speaker = custom_mix_bigtts | |list |null |
| | | | | | \
|req_params.mix_speaker.speakers[i].source_speaker |混音源音色名（支持大小模型音色和复刻2.0音色） | |string |"" |
| | | | | | \
|req_params.mix_speaker.speakers[i].mix_factor |混音源音色名影响因子 | |float |0 |

单音色请求参数示例：
```JSON
{
    "user": {
        "uid": "12345"
    },
    "req_params": {
        "text": "明朝开国皇帝朱元璋也称这本书为,万物之根",
        "speaker": "zh_female_shuangkuaisisi_moon_bigtts",
        "audio_params": {
            "format": "mp3",
            "sample_rate": 24000
        },
      }
    }
}
```

mix请求参数示例：
```JSON
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
            "speakers": [{
                "source_speaker": "zh_male_bvlazysheep",
                "mix_factor": 0.3
            }, {
                "source_speaker": "BV120_streaming",
                "mix_factor": 0.3
            }, {
                "source_speaker": "zh_male_ahu_conversation_wvae_bigtts",
                "mix_factor": 0.4
            }]
        }
    }
}
```

2.3 响应Response

* 音频响应数据，其中data对应合成音频base64音频数据：

```JSON
{
    "code": 0,
    "message": "",
    "data" : {{STRING}}
}
```


* 文本响应数据，其中sentence对应合成文本数据（包含时间戳）：

```JSON
{
    "code": 0,
    "message": "",
    "data" : null,
    "sentence": <object>
}
```

示例json：
```JSON
{
    "code": 0,
    "message": "",
    "data": null,
    "sentence": {
        "text": "其他人。",
        "words": [
            {
                "confidence": 0.8531248,
                "endTime": 0.315,
                "startTime": 0.205,
                "word": "其"
            },
            {
                "confidence": 0.9710379,
                "endTime": 0.515,
                "startTime": 0.315,
                "word": "他"
            },
            {
                "confidence": 0.9189944,
                "endTime": 0.815,
                "startTime": 0.515,
                "word": "人。"
            }
        ]
    }
}
```


* 合成音频结束对应的成功响应：
   * 其中usage字段默认不存在，仅在header中插入需要返回用量的标记后会新增。

```JSON
{
    "code": 20000000,
    "message": "ok",
    "data": null,
    "usage": {"text_words":10}
}
```

<span id="60a09161"></span>
# 3 错误码

| | | | \
|Code |Message |说明 |
|---|---|---|
| | | | \
|20000000 |ok |音频合成结束的成功状态码 |
| | | | \
|40402003 |TTSExceededTextLimit:exceed max limit |提交文本长度超过限制 |
| | | | \
|45000000 |\
| |speaker permission denied: get resource id: access denied |音色鉴权失败，一般是speaker指定音色未授权或者错误导致 |\
| | | |
|^^| | | \
| |quota exceeded for types: concurrency |并发限流，一般是请求并发数超过限制 |
| | | | \
|55000000 |服务端一些error |服务端通用错误 |

<span id="8466052c"></span>
# 4 示例Samples
<span id="0947752e"></span>
## Python：

<Attachment link="https://p9-arcosite.byteimg.com/tos-cn-i-goo7wpa0wc/b86fde682e2649e1a5498bfd71f21be3~tplv-goo7wpa0wc-image.image" name="tts_http_demo.py" ></Attachment>



