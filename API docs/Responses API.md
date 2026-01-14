Responses API  
  
一、创建相应模型  
 POST https://ark.cn-beijing.volces.com/api/v3/responses   
本文介绍 Responses API 创建模型请求时的输入输出参数，供您使用接口时查阅字段含义。  
*Tips：一键展开折叠，快速检索内容  
*说明  
*打开页面右上角开关后，ctrl + f 可检索页面内所有内容。  
*   
  
Tips：一键展开折叠，快速检索内容  
  
鉴权说明  
快速入口  
 模型列表     模型计费      Responses API 教程     上下文缓存教程     API Key  
  
本接口支持 API Key /Access Key 鉴权，详见鉴权认证方式。  
  
请求参数  
跳转 响应参数  
请求体  
  
model string 必选  
您需要调用的模型的 ID （Model ID），开通模型服务，并查询 Model ID 。支持的模型请参见 模型列表。  
当您有多个应用调用模型服务或更细粒度权限管理，可通过 Endpoint ID 调用模型。  
  
input  string / array 必选  
输入的内容，模型需要处理的输入信息。  
*信息类型  
*   
*文本输入 string  
*输入给模型的文本类型信息，等同于使用 user 角色输入的文本信息。  
  
*输入的元素列表 array  
*输入给模型的信息元素，可以包括不同的信息类型。  
  
*信息类型  
*   
*输入的消息 object  
*发送给模型的消息，其中角色用于指示指令遵循的优先级层级。由 developer 或 system 角色给出的指令优先于 user 角色给出的指令。assistant 角色的消息通常被认为是模型在先前交互中生成的回复。  
  
*   
*上下文元素 object  
*表示模型生成回复时需参考的上下文内容。该项可以包含文本、图片和视频输入，以及先前助手的回复和工具调用的输出。  
*   
*   
*模型思维链信息 object  
*在模型生成响应时使用的思维链信息。如果需要手动管理，需要设置该字段，以便在后续的对话中进行管理。  
*仅模型 doubao-seed-1-8-251228、deepseek-v3-2-251201支持设置思维链信息。  
*说明  
*推荐在 Responses API 中使用 previous_response_id，API 将自动保存历史轮次的思考内容，并在多轮交互中回传给模型。  
  
*属性  
*   
*input.content string / array     
*用于生成回复的文本、图片或视频输入，也可以包含先前助手的回复内容。  
  
*   
*input.role string    
*输入消息的角色，可以是 user，system ，assistant或 developer。  
*   
*input.type string  
*消息输入的类型，此处应为message。  
*   
*input.partial boolean  
*模型续写模式。  
*在 input 列表里设置最后一条消息的 role 为assistant，并设置 partial 为 true开启续写模式，模型会基于 content 内容进行续写。在续写模式下，partial 为必填项，具体使用见文档。  
*消息类型  
*   
*文本输入 string  
*输入给模型的文本。  
*   
*输入的内容列表 array  
*包含一个或多个输入项的列表，每个输入项可包含不同类型的内容。  
*   
*内容类型  
*   
*输入模型的文本 object  
*输入模型的文本。  
  
*输入模型的图片 object  
*输入模型的图片。多模态理解示例见文档。  
  
*   
*输入模型的视频 object  
*输入模型的视频。多模态理解示例见文档。  
  
*   
*输入模型的文件 object  
*输入模型的文件。当前仅支持PDF文件。多模态理解示例见文档。  
*   
*属性  
*   
*input.content.text string    
*输入模型的文本。  
*   
*input.content.type string    
*输入项的类型，此处应为input_text。  
*   
*input.content.translation_options object   
*特定的翻译模型支持该字段，配置翻译场景下的语种等信息。  
*支持模型为 doubao-seed-translation-250728 。   
*   
*属性 >  
*   
*input.content.translation_options.source_language string  
*需要翻译的信息的源语言语种。  
*   
*input.content.translation_options.target_language string    
*需要翻译为何目标语言语种。  
*属性  
*   
*input.content.type string    
*输入为图片类型，此处应为input_image。  
*   
*input.content.file_id string   
*文件ID。  
*文件ID是通过Files API上传文件后返回的id。  
*file_id对应的文件类型需要和type保持一致，且文件状态需要为active。  
*   
*input.content.image_url string   
*要发送给模型的图片 URL。可以是完整的 URL，或以 data URL 形式编码的 base64 图片。  
*   
*input.content.detail string   
*发送给模型的图片细节级别。可选值为 high、low 或 auto，默认为 auto。  
*   
*input.content.image_pixel_limit  object / null 默认值 null  
*允许设置图片的像素大小限制，如果不在此范围，则会等比例放大或者缩小至该范围内。  
*注意：图片像素范围需在 [196,3600w]，否则会直接报错。  
*生效优先级：高于 detail 字段，即同时配置 detail 与 image_pixel_limit 字段时，生效 image_pixel_limit 字段配置。  
*若 min_pixels / max_pixels 字段未设置，使用 detail 设置配置的值对应的 min_pixels / max_pixels 值。  
*   
*属性 >  
*   
*input.content.image_pixel_limit.max_pixels integer  
*doubao-seed-1.8 之前的模型取值范围：(min_pixels,  4014080]，doubao-seed-1.8 模型的取值范围：(min_pixels, 9031680)。  
*传入图片最大像素限制，大于此像素则等比例缩小至 max_pixels 字段取值以下。  
*若未设置，则取值为 detail 设置配置的值对应的 max_pixels 值。  
*   
*input.content.image_pixel_limit.min_pixels  
*doubao-seed-1.8 之前的模型取值范围：[3136,  max_pixels)，doubao-seed-1.8 模型的取值范围：[1764,  max_pixels)。  
*传入图片最小像素限制，小于此像素则等比例放大至 min_pixels 字段取值以上。  
*若未设置，则取值为 detail 设置配置的值对应的 min_pixels 值。  
*属性  
*   
*input.content.type string    
*输入为视频类型，此处为input_video。  
*   
*input.content.file_id string   
*文件ID。  
*文件ID是通过Files API上传文件后返回的id。  
*file_id对应的文件类型需要和type保持一致，且文件状态需要为active。  
*   
*input.content.video_url string   
*要发送给模型的视频 URL。可以是完整的 URL，或以 data URL 形式编码的 base64 视频。  
*   
*input.content.fps float  
*每秒钟从视频中抽取指定数量的图像，取值范围：[0.2, 5]。  
*如果使用file_id参数，fps参数则会失效。*属性  
*   
*input.content.type string    
*输入为文件类型，此处为input_file。  
*   
*input.content.file_id string   
*文件ID。  
*文件ID是通过Files API上传文件后返回的id。  
*file_id对应的文件类型需要和type保持一致，且文件状态需要为active。  
*   
*input.content.file_data string   
*文件内容的Base64编码。单个文件大小要求不超过50 MB。  
*   
*input.content.filename string  
*文件名。当使用file_data时该参数必填。  
*   
*input.content.file_url string  
*文件的可访问URL。对应文件的大小要求不超过50 MB。  
*  
*属性  
*   
*输入的信息object  
*历史请求中，发给模型的信息。  
  
*   
*工具函数信息 object  
*模型调用工具函数的信息  
  
*   
*工具返回的信息 object  
*调用工具后，工具返回的信息  
  
*属性  
*   
*input.content array    
*与 输入的信息 中 content 字段的结构完全一致。  
*   
*input.role string    
*输入消息的角色，可选值： system，user 或 developer。  
*   
*input.type string  
*消息输入的类型，此处应为message。  
*   
*input.status string   
*项目状态，可选值：in_progress，completed 或 incomplete。  
*属性  
*   
*input.arguments string    
*要传递给函数的参数的 JSON 字符串。  
*   
*input.call_id string    
*模型生成的函数工具调用的唯一ID。  
*   
*input.name string    
*要运行的函数的名称。  
*   
*input.type string    
*工具调用的类型，始终为 function_call。  
*   
*input.status string  
*该项的状态。  
*属性  
*   
*input.call_id string    
*模型生成的函数工具调用的唯一 ID。  
*   
*input.output string    
*调用工具后，工具输出的结果。  
*   
*input.type string    
*工具调用的类型，始终为 function_call_output。  
*   
*input.status string  
*该项的状态。  
*属性  
*   
*input.id string  
*思维链信息的唯一标识。  
*   
*input.type string  
*输入对象的类型，此处应为 reasoning。  
*   
*input.summary array  
*思维链内容。  
  
*属性  
*   
*input.summary.text string  
*思维链内容的文本部分。  
*   
*input.summary.type string  
*对象的类型，此处应为summary_text。  
  
信息类型  
  
instructions string / null   
在模型上下文中插入系统消息或者开发者作为第一条指令。当与 previous_response_id 一起使用时，前一个回复中的指令不会被继承到下一个回复中。这样可以方便地在新的回复中替换系统（或开发者）消息。  
不可与缓存能力一起使用。配置了instructions 字段后，本轮请求无法写入缓存和使用缓存，表现为：  
caching 字段配置为 {"type":"enabled"} 时报错。  
传入带缓存的 previous_response_id 时，缓存输入（cached_tokens）为0。  
  
previous_response_id string / null   
上一个模型回复的唯一标识符。使用该标识符可以实现多轮对话。  
note：在多轮连续对话中，建议在每次请求之间加入约 100 毫秒的延迟，否则可能会导致调用失败。  
  
expire_at integer 默认值：创建时刻+259200   
取值范围：(创建时刻, 创建时刻+604800]，即最多保留7天。  
设置存储的过期时刻，需传入 UTC Unix 时间戳（单位：秒），对 store（上下文存储） 和 caching（上下文缓存） 都生效。详细配置及示例代码说明请参见文档。  
注意：缓存存储时间计费，过期时刻-创建时刻 ，不满 1 小时按 1 小时计算。  
  
max_output_tokens integer / null   
模型输出最大 token 数，包含模型回答和思维链内容。  
  
thinking object 默认值：取决于调用的模型   
控制模型是否开启深度思考模式。默认开启深度思考模式，可以手动关闭。  
*属性  
*   
*thinking.type string     
*取值范围：enabled， disabled，auto。  
*enabled：开启思考模式，模型一定先思考后回答。  
*disabled：关闭思考模式，模型直接回答问题，不会进行思考。  
*auto：自动思考模式，模型根据问题自主判断是否需要思考，简单题目直接回答。  
  
属性  
  
reasoning object 默认值 {"effort": "medium"}  
限制深度思考的工作量。减少深度思考工作量可使响应速度更快，并且深度思考的 token 用量更小。  
*属性  
  
*reasoning.effort string  
*仅模型 doubao-seed-1-8-251228、doubao-seed-1-6-lite-251015、doubao-seed-1-6-251015 支持该字段，使用说明见文档。  
*取值范围：minimal，low，medium，high。  
*minimal：关闭思考，直接回答。  
*low：轻量思考，侧重快速响应。  
*medium：均衡模式，兼顾速度与深度。  
*high：深度分析，处理复杂问题。  
*关于thinking.type、reasoning.effort的使用说明如下：  
*thinking.type 取值为enabled：支持配置reasoning.effort。当reasoning.effort取值为minimal时，则关闭思考，直接回答。  
*thinking.type 取值为disabled：reasoning.effort 仅支持取值minimal；配置为low、medium、high时，请求报错。  
  
属性  
  
caching object 默认值 {"type": "disabled"}  
是否开启缓存，阅读文档，了解缓存的具体使用方式。  
不可与 instructions 字段、tools（除自定义函数 Function Calling 外）字段一起使用。  
*属性  
*   
*caching.type string     
*取值范围：enabled， disabled。  
*enabled：开启缓存。  
*disabled：关闭缓存。  
*   
*caching.prefix boolean 默认值 false  
*true：仅创建公共前缀缓存，模型不回复。  
*false：不创建公共前缀缓存。  
  
属性  
  
store boolean / null 默认值 true  
是否储存生成的模型响应，以便后续通过 API 检索。详细上下文管理使用说明，请见文档。  
false：不储存，对话内容不能被后续的 API 检索到。  
true：储存当前模型响应，对话内容能被后续的 API 检索到。  
  
stream boolean / null 默认值 false  
响应内容是否流式返回。流式输出示例见文档。  
false：模型生成完所有内容后一次性返回结果。  
true：按 SSE 协议逐块返回模型生成内容，并以一条 data: [DONE]消息结束。  
  
temperature float / null 默认值 1  
取值范围： [0, 2]。  
采样温度。控制了生成文本时对每个候选词的概率分布进行平滑的程度。当取值为 0 时模型仅考虑对数概率最大的一个 token。  
较高的值（如 0.8）会使输出更加随机，而较低的值（如 0.2）会使输出更加集中确定。  
通常建议仅调整 temperature 或 top_p 其中之一，不建议两者都修改。  
  
top_p float / null 默认值 0.7  
取值范围： [0, 1]。  
核采样概率阈值。模型会考虑概率质量在 top_p 内的 token 结果。当取值为 0 时模型仅考虑对数概率最大的一个 token。  
 0.1 意味着只考虑概率质量最高的前 10% 的 token，取值越大生成的随机性越高，取值越低生成的确定性越高。通常建议仅调整 temperature 或 top_p 其中之一，不建议两者都修改。  
  
text object  
模型文本输出的格式定义，可以是自然语言，也可以是结构化的 JSON 数据。详情请看结构化输出。  
*属性  
*   
*text.format object 默认值 { "type": "text" }  
*指定模型文本输出的格式。  
  
*属性  
*   
*文本格式 object  
*响应格式为自然语言。  
  
*   
*JSON Object object   
*响应格式为 JSON 对象。结构化输出示例，见文档。  
*该能力尚在 beta 阶段，请谨慎在生产环境使用。  
  
*   
*JSON Schema  object   
*响应格式为 JSON 对象，遵循schema字段定义的 JSON结构。结构化输出示例，见文档。  
*该能力尚在 beta 阶段，请谨慎在生产环境使用。  
*   
*属性  
*text.format.type string    
*回复格式的类型，此处应为 text。  
*属性  
*   
*text.format.type string    
*回复格式的类型，此处应为 json_object。  
*属性  
*   
*text.format.type string    
*回复格式的类型，此处应为 json_schema。  
*   
*text.format.name string    
*用户自定义的JSON结构的名称。  
*   
*text.format.schema object    
*回复格式的JSON格式定义，以JSON Schema对象的形式描述。  
*   
*text.format.description string / null   
*回复用途描述，模型将根据此描述决定如何以该格式回复。  
*   
*text.format.strict boolean / null  默认值 false  
*是否在生成输出时，启用严格遵循模式。  
*true：模型将始终遵循schema字段中定义的格式。  
*false：模型将尽可能遵循schema字段中定义的结构。  
  
属性  
  
tools array  
模型可以调用的工具，当您需要让模型调用工具时，需要配置该结构体。  
*工具类型  
*   
*当前支持多种调用方式，包括  
*内置工具（Built-in tools）：由方舟提供的预置工具，用以扩展模型内容，如豆包助手、联网搜索工具、图像处理工具、私域知识库搜索工具等。  
*MCP工具：通过自定义 MCP 服务器与第三方系统集成。  
*自定义工具（Function Calling）：您自定义的函数，使模型能够使用强类型参数和输出调用您自己的代码，使用示例见 文档 。  
  
*   
*   
*   
  
*豆包助手  
*使用豆包助手，快速集成豆包app同款AI能力。详情请参考 豆包助手文档。  
*注意：使用前需开通“豆包助手”功能。  
*   
*tools.type string 必选  
*工具类型，此处填写工具名称，应为doubao_app。  
*   
*tools.feature object   
*豆包助手子功能。  
*   
*   
*   
*   
*   
*tools.user_location object 默认值{"type": "approximate"}  
*用户地理位置，用于优化对话与搜索结果，包含 type、country、city、region 字段。示例如下：  
*   
*注意：填写 type 后，country、city、region 中 至少1个字段有有效值。  
*tools.feature.chat object  
*日常沟通功能，豆包同款自由对话，默认关闭。  
  
*tools.feature.chat.type string 默认值disabled  
*取值范围：enabled， disabled。  
*enabled：开启此功能。  
*disabled：关闭此功能。  
*tools.feature.chat.role_description string 默认值：你的名字是豆包,有很强的专业性。  
*使用豆包助手时修改角色设定。  
*此字段与system prompt、instructions 互斥。  
*tools.feature.deep_chat object  
*深度沟通功能，豆包同款深度思考对话，默认关闭。  
  
*tools.feature.deep_chat.type string 默认值disabled  
*取值范围：enabled， disabled。  
*enabled：开启此功能。  
*disabled：关闭此功能。  
*tools.feature.deep_chat.role_description string 默认值：你的名字是豆包,有很强的专业性。  
*使用豆包助手时修改角色设定。  
*此字段与system prompt、instructions 互斥。  
*  
*tools.feature.ai_search object  
*联网搜索功能，豆包同款AI搜索能力，默认关闭。  
  
*tools.feature.ai_search.type string 默认值 disabled  
*取值范围：enabled， disabled。  
*enabled：开启此功能。  
*disabled：关闭此功能。  
*tools.feature.ai_search.role_description string 默认值：你的名字是豆包,有很强的专业性。  
*使用豆包助手时修改角色设定。  
*此字段与system prompt、instructions 互斥。  
*tools.feature.reasoning_search object  
*边想边搜功能，豆包同款结合思考过程的智能搜索能力，默认关闭。  
  
*tools.feature.reasoning_search.type string 默认值 disabled  
*取值范围：enabled， disabled。  
*enabled：开启此功能。  
*disabled：关闭此功能。  
*tools.feature.reasoning_search.role_description string 默认值：你的名字是豆包,有很强的专业性。  
*使用豆包助手时修改角色设定。  
*此字段与system prompt、instructions 互斥。  
*Function Calling  
*tools.type string 必选  
*工具类型，此处应为 function。  
*   
*tools.name string    
*调用的函数的名称。  
*   
*tools.description string  
*调用函数的描述，大模型会用它来判断是否调用这个函数。  
*   
*tools.parameters object    
*函数请求参数，以 JSON Schema 格式描述。具体格式请参考 JSON Schema 文档，格式如下：  
*   
*其中，  
*所有字段名大小写敏感。  
*parameters 须是合规的 JSON Schema 对象。  
*建议用英文字段名，中文置于 description 字段中。  
*   
*tools.strict boolean  默认值 true  
*是否强制执行严格的参数验证。默认为true。  
*联网搜索工具  
*在互联网上搜索与该提示相关的资源，详情请参考 Web Search 基础联网搜索。  
*注意：使用前需开通“联网内容插件”组件。  
*   
*tools.type string 必选  
*工具类型，此处填写工具名称，应为web_search。  
*   
*tools.sources string[]   
*选择联网搜索的附加内容源。可选头条图文、抖音百科、墨迹天气。  
*toutiao ：联网搜索的附加头条图文内容源。  
*douyin ：联网搜索的附加抖音百科内容源。  
*moji ：联网搜索的附加墨迹天气内容源。  
*   
*tools.limit integer 默认值 10  
*取值范围： [1, 50]。  
*单轮搜索最大召回条数。  
*说明：影响输入规模与性能，单次搜索最多返回20条结果（单轮可能有多次搜索），默认召回10条。  
*   
*tools.user_location object 默认值{"type": "approximate"}  
*用户地理位置，用于天气查询等场景，包含 type、country、city、region 字段。示例如下：  
  
*注意：填写 type 后，country、city、region 中 至少1个字段有有效值。  
*   
*tools.max_keyword integer    
*取值范围： [1, 50]。  
*工具一轮使用，最大并行搜索关键词的数量。  
*举例：如模型判断需要搜索关键词：“大模型最新进展”，“2025年科技创新”，“火山方舟进展”。  
*此时max_keyword = 1，则实际仅搜索第一个关键词“大模型最新进展”。  
*图像处理工具  
*使用画点、画线、旋转、缩放、框选/裁剪关键区域等基础图像处理工具，详情请参考 Image Process 图像处理工具。  
*   
*tools.type string 必选  
*工具类型，此处填写工具名称，应为image_process。  
*   
*tools.point object  
*画点/连线功能开关，控制是否启用点绘制与连线功能。  
  
*   
*tools.grounding object  
*框选/裁剪功能开关，控制是否启用关键区域框选或裁剪。  
  
*   
*tools.zoom object  
*缩放功能开关，控制是否启用全图/指定区域缩放（支持0.5-2.0倍）。  
  
*tools.rotate object  
*旋转功能开关，控制是否启用顺时针旋转（支持0-359度）。  
  
*属性  
*tools.point.type string  默认值 enabled  
*取值范围：enabled， disabled。  
*enabled：开启此功能。  
*disabled：关闭此功能。  
*属性  
*tools.grounding.type string  默认值 enabled  
*取值范围：enabled， disabled。  
*enabled：开启此功能。  
*disabled：关闭此功能。  
*属性  
*tools.zoom.type string  默认值 enabled  
*取值范围：enabled， disabled。  
*enabled：开启此功能。  
*disabled：关闭此功能。  
*属性  
*tools.rotate.type string  默认值 enabled  
*取值范围：enabled， disabled。  
*enabled：开启此功能。  
*disabled：关闭此功能。  
*MCP 工具  
*   
*tools.type string 必选  
*工具类型，此处填写工具名称，应为mcp。  
*   
*tools.server_label string 必选  
*MCP Server标签，建议设定与工具用途/Server名称一致。  
*   
*tools.server_url string 必选  
*MCP Server访问地址。  
*   
*tools.headers object  
*要发送至 MCP 服务器的可选 HTTP 请求头，用于身份验证或其他用途。包含：  
*Authorization 鉴权信息（不存储）。  
*自定义key-value。  
*   
*tools.require_approval object/string  默认值 always  
*指定哪些 MCP 服务器工具需要授权。  
*   
*   
*tools.allowed_tools array/object  
*工具加载范围，默认包含当前MCP Server所有工具。  
*   
*属性  
*工具批准设置 string   
*取值范围：  
*always：所有工具需用户确认后调用。  
*never：所有工具无需确认，直接调用（可能存在安全风险）。  
*   
*工具批准筛选 object   
*指定 MCP 服务器的哪些工具需要审批。可以是 always、never或与需要审批的工具关联的过滤器对象。  
  
*属性  
*tools.require_approval.always object  
*指定哪些工具需要用户确认批准。  
*   
*   
*tools.require_approval.never object  
*指定哪些工具不需要用户确认批准使用。  
*   
*属性  
*tools.require_approval.always.tool_names array  
*需要用户确认批准的工具名称列表。  
*属性  
*tools.require_approval.never.tool_names array  
*不需要用户确认批准的工具名称列表。  
*属性  
*工具加载范围 array  
*允许加载的工具名称的字符串数组。  
*   
*工具筛选 object  
*指定 MCP 服务器的哪些工具允许使用。  
  
*属性  
*tools.allowed_tools.tool_names array  
*允许的工具名称列表。  
*私域知识库搜索工具  
*tools.type string 必选  
*工具类型，此处填写工具名称，应为knowledge_search。  
*   
*tools.knowledge_search_id  string 必选  
*填写需使用的私域知识库ID。  
*   
*tools.limit integer 默认值 10  
*取值范围： [1, 200]。  
*最大可被采用的搜索结果。  
*   
*tools.max_keyword integer    
*取值范围： [1, 50]。  
*工具一轮使用，最大并行搜索关键词的数量。  
*举例：如模型判断需要搜索关键词：“大模型最新进展”，“2025年科技创新”，“火山方舟进展”。  
*此时max_keyword = 1，则实际仅搜索第一个关键词“大模型最新进展”。  
*   
*tools.doc_filters  object  
*检索过滤条件，用户可以指定结果过滤的字段。  
*支持对 doc 的 meta 信息过滤。  
*详细使用方式和支持字段见filter表达式，可支持对 doc_id 做筛选。  
*此处用过过滤的字段，需要在 collection/create 时添加到 index_config 的 fields 上。  
*例如：  
*单层 filter：  
  
*多层 filter：  
  
*   
*tools.description  string  
*私域知识库的描述信息。  
*   
*tools.dense_weight  float  默认值 0.5  
*取值范围： [0.2, 1]。  
*稠密向量的权重。  
*1 表示纯稠密检索 ，趋向于 0 表示纯字面检索。  
*只有在请求的知识库使用的是混合检索时有效，即索引算法为 hnsw_hybrid。  
*   
*tools.ranking_options  object   
*检索后处理选项。可参考 知识库API文档 post_processing 字段。  
  
*属性  
*tools.ranking_options.rerank_switch bool 默认值 false  
*是否自动对检索结果做 rerank。  
*若设置为true，则会自动请求 rerank 模型排序。  
*   
*tools.ranking_options.retrieve_count integer 默认值 25  
*进入重排的切片数量。此项只有在 rerank_switch 为 true 时生效。  
*注意：retrieve_count 需要大于等于 limit，否则会抛出错误。  
*   
*tools.ranking_options.get_attachment_link bool 默认值 false  
*是否获取切片中图片的临时下载链接。  
*   
*tools.ranking_options.chunk_diffusion_count integer 默认值 0  
*取值范围 [0, 5]  
*检索阶段返回命中切片的上下几片邻近切片。默认为 0，表示不进行 chunk diffusion。  
*   
*tools.ranking_options.chunk_group bool 默认值 false  
*文本聚合。  
*默认不聚合，对于非结构化文件，考虑到原始文档内容语序对大模型的理解，可开启文本聚合。开启后，会根据文档及文档顺序，对切片进行重新聚合排序返回。  
*   
*tools.ranking_options.rerank_model string   默认值 "base-multilingual-rerank"   
*rerank 模型选择。仅在 rerank_switch 为 True 的时候生效。  
*可选模型：   
*（推荐）"base-multilingual-rerank"：速度快、长文本、支持70+种语言。  
*"m3-v2-rerank"：常规文本、支持100+种语言。  
*   
*tools.ranking_options.rerank_only_chunk bool 默认值 false  
*是否仅根据 chunk 内容计算重排分数。可选值：   
*True：只根据 chunk 内容计算分   
*False：根据 chunk title + 内容 一起计算排序分  
  
工具类型  
  
tool_choice string / object  
仅 doubao-seed-1-6-*** 模型支持此字段。  
本次请求，模型返回信息中是否有待调用的工具。  
当没有指定工具时，none 是默认值。如果存在工具，则 auto 是默认值。  
*可选类型  
*   
*工具选择模式 string  
*控制模型返回是否包含待调用的工具。  
*none ：模型返回信息中不可含有待调用的工具。  
*required ：模型返回信息中必须含待调用的工具。选择此项时请确认存在适合的工具，以减少模型产生幻觉的情况。  
*auto ：模型自行判断返回信息是否有待调用的工具。  
*   
*工具调用 object  
*指定待调用工具的范围。模型返回信息中，只允许包含以下模型信息。选择此项时请确认该工具适合用户需求，以减少模型产生幻觉的情况。  
*   
*属性  
*   
*tool_choice.type string    
*调用的类型。  
*如果为自定义Function此处应为 function，此时 tool_choice.name 字段为必选。  
*如果为内置工具，此处填写工具名称，请参考 Responses API 内置工具。  
*   
*tool_choice.name string   
*待调用工具的名称。  
*如果 tool_choice.type 为 function，此项为必选。  
  
可选类型  
  
max_tool_calls  integer    
取值范围： [1, 10]。  
最大工具调用轮次（一轮里不限制次数）。在工具调用达到此限制次数后，提示模型停止更多工具调用并进行回答。  
注意：该参数为尽力而为（best effort）机制，不保证成功，最终调用次数会受模型推理效果、工具返回结果有效性等因素影响。  
豆包助手不支持此参数。  
Web Search 基础联网搜索工具的默认值 3。  
Image Process 图像处理工具的默认值 10，不支持修改。  
Knowledge Search 私域知识库搜索工具的默认值为3。  
context_management  object    
上下文管理策略，帮助模型有效利用上下文窗口。  
*属性  
  
*context_management.edits array  
*支持的上下文编辑策略，用于管理上下文中思考块和工具调用内容。  
  
*  
*策略类型  
*   
*思考块清除 object  
*在开启思考时管理思维链内容。  
  
*   
*工具调用内容清除 object  
*在对话上下文增长超过配置的阈值时清除工具调用内容。  
  
*属性  
*   
*context_management.edits.type string  
*上下文编辑策略类型，此处应为clear_thinking。  
*   
*context_management.edits.keep object/string  
*思维链保留策略。  
  
*类型  
*   
*保留最近 N 轮思维链 object  
  
*保留所有思维链 string  
*保留所有思维链，此处应为 all。  
*属性  
*context_management.edits.keep.type string  
*思维链保留策略类型，此处应为thinking_turns。  
*   
*context_management.edits.keep.value integer 默认值 1  
*保留最近 N 轮的思维链。  
*属性  
*   
*context_management.edits.type string  
*上下文编辑策略类型，此处应为clear_tool_uses。  
*   
*context_management.edits.keep object  
*工具调用内容保留策略。  
  
*context_management.edits.exclude_tools array  
*不会被清除的工具名称列表，用于保留重要上下文。  
*   
*context_management.edits.clear_tool_input boolean 默认值 false  
*是否清除工具调用参数。  
*   
*context_management.edits.trigger object  
*触发工具调用内容清除策略的阈值。  
  
*属性  
*   
*context_management.edits.keep.type string  
*工具调用内容保留策略类型，此处应为tool_uses。  
*   
*context_management.edits.keep.value integer 默认值 3   
*保留最近 N 轮工具调用内容。  
*属性  
*   
*context_management.edits.trigger.type string  
*触发工具调用内容清除策略类型，此处应为tool_uses。  
*   
*context_management.edits.trigger.value integer   
*工具调用达到 N 轮时触发清除策略。  
  
属性  
  
响应参数  
跳转 请求参数  
非流式调用返回  
返回一个 response object。  
流式调用返回  
服务器会在生成 Response 的过程中，通过 Server-Sent Events（SSE）实时向客户端推送事件。具体事件介绍请参见 流式响应。  
  
二、查询模型响应  
GET https://ark.cn-beijing.volces.com/api/v3/responses/{response_id}  
通过 response id 获取模型响应。  
  
快速入口  
鉴权说明  
本接口仅支持 API Key 鉴权，请在 获取 API Key 页面，获取长效 API Key。  
  
模型列表      
模型计费       
Responses API 教程      
上下文缓存教程      
API Key  
  
请求参数   
路径参数  
  
response_id string 必选  
待检索的响应 id。  
响应参数  
如果您调用的 response 响应已完成，模型会返回对应的 response object。  
如果您调用的 response 响应未完成，模型会返回错误码。  
  
三、获取响应上下文  
GET https://ark.cn-beijing.volces.com/api/v3/responses/{response_id}/input_items?after={after}&before={before}&limit={limit}&order={order}&include[]={include}  
获取某次模型响应对应的全部上下文信息。  
  
快速入口  
鉴权说明  
本接口仅支持 API Key 鉴权，请在 获取 API Key 页面，获取长效 API Key。  
  
模型列表      
模型计费       
Responses API 教程      
上下文缓存教程      
API Key  
  
请求参数   
跳转 响应参数  
路径参数  
  
response_id string 必选  
待检索上下文元素所对应的响应 id。  
  
查询参数  
在 URL String 中传入。  
  
after string/ null  
返回该 ID 之后的输入项。  
  
before string/ null  
返回该 ID 之前的输入项。  
  
include[] array/ null  
用于指定在响应中要额外包含的字段。部分接口默认返回基础字段，通过 include 可让服务端补充返回更多信息。  
属性  
message.input_image.image_url  
包含输入消息中的图像 URL。  
图像为 url 时，返回url。  
图像为 base64 编码时，返回 base64 编码信息。  
  
limit integer 默认值：100  
控制单次返回的最大项目数。  
取值范围： 1 ~ 100。  
  
order string 默认值：desc  
控制输入项的排序方式。  
 asc：按照正序排列。  
desc：按照倒序排列。  
响应参数  
跳转 请求参数  
返回本次响应对应的所有上下文元素。  
object string  
固定为list。  
  
data object[] / null  
上下文元素列表，与 创建模型请求 时的 input（输入的元素列表）字段结构完全一致。  
如果请求中引用了 previous_response_id，服务器也会返回previous_response 包含的上下文。  
  
first_id string  
列表中第一条数据的 ID。  
  
has_more boolean  
标识是否还有更多数据未返回。  
true：存在未返回的数据。  
false：已返回全部数据。  
  
last_id string  
列表中最后一条数据的 ID。  
  
四、删除模型响应  
DELETE https://ark.cn-beijing.volces.com/api/v3/responses/{response_id}  
本文介绍如何删除指定 ID 的模型请求。  
  
快速入口  
鉴权说明  
本接口仅支持 API Key 鉴权，请在 获取 API Key 页面，获取长效 API Key。  
  
模型列表            
模型计费         
模型调用教程      
API Key  
  
请求参数  
路径参数  
  
response_id string 必选  
待删除请求的id。  
  
响应参数  
  
id string  
待删除请求的id。  
  
object string  
固定为 response。  
  
deleted boolean  
取值范围：  
true：删除成功。  
false：未删除成功。  
  
五、  
六、创建模型请求 或 获取模型响应 后，模型会返回一个 response 对象。本文为您介绍 response 对象包含的详细参数。  
*Tips：一键展开折叠，快速检索内容  
*说明  
*打开页面右上角开关后，ctrl + f 可检索页面内所有内容。  
*   
  
Tips：一键展开折叠，快速检索内容  
  
说明  
获取模型响应时，模型返回的 response 对象不包含思维链内容。  
  
created_at integer  
本次请求创建时间的 Unix 时间戳（秒）。  
  
error object / null  
模型未能生成响应时返回的错误对象。  
code：相应的错误码。  
message：错误描述。  
  
id string  
本次请求的唯一标识。  
  
incomplete_details object / null  
响应未能完成的细节。  
reason：响应未能完成的原因。  
  
instructions string / null  
在模型上下文中插入一条系统（或开发者）消息，作为首项。  
当与 previous_response_id 一起使用时，前一响应中的指令不会延续到下一响应。  
  
max_output_tokens integer / null  
模型输出最大 token 数，包含模型回答和思维链内容。  
  
model string  
本次请求实际使用的模型名称和版本。  
  
objectstring  
固定为response。  
  
output array  
模型的输出消息列表，包含模型响应本次请求生成的回答、思维链、工具调用。  
*属性  
*   
*模型回答 object  
*模型回答，不包含思维链。  
*   
  
*模型思维链  
*本次请求，当触发深度思考时，模型会返回问题拆解的思维链内容。  
  
*   
*工具调用  
*本次请求，模型根据信息认为需要调用的工具信息以及对应参数。  
  
*属性  
*   
*output.content array   
*输出消息的内容。  
  
*   
*output.role string   
*输出信息的角色，固定为assistant。  
*   
*output.status string  
*输出消息的状态。  
*   
*output.id string  
*此回答的唯一标识。  
*   
*output.type string   
*输出消息的类型，此处应为message。  
*   
*output.partial boolean   
*模型开启续写模式时会返回该字段，此处应为true。  
*属性  
*   
*文本回答 object  
*模型回答的文本消息。  
  
*属性  
*   
*output.content.text string   
*模型回答的文本内容。  
*   
*output.content.type string   
*模型回答的类型，固定为output_text。  
*属性  
*   
*output.summary array   
*思维链内容。  
*   
*   
*output.type string   
*本输出对象的类型，此处应为 reasoning。  
*   
*output.status string  
*本次思维链内容返回的状态。  
*   
*output.id string  
*本思维链消息的唯一标识。  
*属性  
*   
*output.summary.text string   
*思维链内容的文本部分。  
*   
*output.summary.type string   
*对象的类型，此处应为 summary_text。  
*属性  
*   
*output.arguments string   
*要传递给函数的参数，格式为 JSON 字符串。  
*   
*output.call_id string   
*本次工具调用信息的唯一 ID 。  
*   
*output.name string   
*要运行的函数的名称。  
*   
*output.type string   
*工具调用的类型，此处应为 function_call。  
*   
*output.status string  
*此时消息返回的状态。  
*   
*output.id string  
*本次输出的唯一标识。  
*MCP 工具  
*output.id string  
*本次输出的唯一标识。  
*   
*output.server_label string   
*MCP Server标签。  
*   
*output.tools object  
*mcp工具返回信息  
  
*McpCall  
*arguments string  
*传递给工具的参数的 JSON 字符串。  
  
*id string  
*本次输出的唯一标识。  
  
*name string  
*运行工具的名称。  
*   
*server_label string  
*MCP Server标签。  
  
*type string  
*始终为 mcp_call。  
  
*error string  
*工具调用中出现的错误（如有）。  
  
*output string  
*工具调用的输出结果。  
*McpListTools  
*id string  
*MCP 列表的唯一标识。  
  
*server_label string  
*MCP Server标签。  
  
*tools  array  
*服务端可用工具。  
*   
*属性  
*tools.input_schema object  
*描述工具输入的 JSON 模式。  
*   
*tools.name string  
*运行工具的名称。  
*   
*tools.annotations object  
*关于该工具的其他说明。  
  
*tools.description string  
*工具描述。  
*联网搜索工具  
*output.tools object  
*mcp工具返回信息  
*   
*属性  
*id string  
*本次输出的唯一标识。  
  
*type string  
*始终为 web_search_call。  
  
*action object  
*此次搜索调用中执行的具体操作的对象。  
  
*属性  
*action.type string  
*一般为 search  
*   
*action.query string  
*搜索内容。  
*   
*action.source string[]   
*联网搜索的附加内容源。可能为头条图文、抖音百科、墨迹天气。  
*toutiao ：联网搜索的附加头条图文内容源。  
*douyin ：联网搜索的附加抖音百科内容源。  
*moji ：联网搜索的附加墨迹天气内容源。  
*图像处理工具  
*output.tools object  
*mcp工具返回信息  
  
*属性  
*type string  
*始终为 image_process。  
  
*point object  
*画点/连线功能开关，是否启用点绘制与连线功能。  
*"type":"enabled"：已开启此功能。  
*"type":"disabled"：未开启此功能。  
*   
*grounding object  
*框选/裁剪功能开关，控制是否启用关键区域框选或裁剪。  
*"type":"enabled"：已开启此功能。  
*"type":"disabled"：未开启此功能。  
*   
*zoom object  
*缩放功能开关，控制是否启用全图/指定区域缩放（支持0.5-2.0倍）。  
*"type":"enabled"：已开启此功能。  
*"type":"disabled"：未开启此功能。  
*   
*rotate object  
*旋转功能开关，控制是否启用顺时针旋转（支持0-359度）。  
*"type":"enabled"：已开启此功能。  
*"type":"disabled"：未开启此功能。  
  
属性  
  
previous_response_id string / null  
本次请求时传入的历史响应ID。  
  
thinking object / null  
是否开启深度思考模式。  
*属性  
*thinking.type string    
*取值范围：enabled， disabled，auto。  
*enabled：开启思考模式，模型一定先思考后回答。  
*disabled：关闭思考模式，模型直接回答问题，不会进行思考。  
*auto：自动思考模式，模型根据问题自主判断是否需要思考，简单题目直接回答。  
  
属性  
  
service_tier string  
本次请求是否使用了TPM保障包。  
default：本次请求未使用TPM保障包额度。  
  
status string  
生成响应的状态。  
completed：响应已完成。  
failed：响应失败。  
in_progress：响应中。  
incomplete：响应未完成。  
  
text object  
用于定义输出的格式，可以是纯文本，也可以是结构化的 JSON 数据。详情请看结构化输出。  
*属性  
*   
*text.format object  
*指定模型必须输出的格式的对象。  
  
*  
*属性  
  
*自然语言输出 object  
*模型回复以自然语言输出。  
  
*   
*JSON Object object  
*响应格式为 JSON 对象。  
  
*   
*JSON Schema object  
*响应格式为 JSON 对象，遵循schema字段定义的 JSON结构。  
  
*text.format.type string   
*回复格式的类型，固定为 text。  
*属性  
*   
*text.format.type string   
*回复格式的类型，固定为 json_object。  
*属性  
  
*text.format.type string   
*回复格式的类型，固定为 json_schema。  
*   
*text.format.name string  
*用户自定义的JSON结构的名称。  
*   
*text.format.schema object  
*回复格式的JSON格式定义，以JSON Schema对象的形式描述。  
*   
*text.format.description string / null  
*回复用途描述，模型将根据此描述决定如何以该格式回复。  
*   
*text.format.strict boolean / null  
*是否在生成输出时，启用严格遵循模式。  
*true：模型将始终遵循schema字段中定义的格式。  
*false：模型将尽可能遵循schema字段中定义的结构。  
  
属性  
  
tools array  
模型可以调用的工具列表。  
*属性  
*   
*tools.function object   
*模型可以调用的类型为function的工具列表。  
  
*属性  
*   
*tools.function.name string   
*调用的函数的名称。  
*   
*tools.function.parameters object   
*函数请求参数，以 JSON Schema 格式描述。具体格式请参考 JSON Schema 文档，格式如下：  
  
*其中，  
*所有字段名大小写敏感。  
*parameters 须是合规的 JSON Schema 对象。  
*建议用英文字段名，中文置于 description 字段中。  
*   
*tools.function.type string   
*工具调用的类型，固定为function。  
*   
*tools.function.description string   
*调用的函数的描述，大模型会使用它来判断是否调用这个函数。  
  
属性  
  
top_p float / null  
核采样概率阈值。  
  
usage object  
本次请求的 token 用量，包括输入 token 数量、输入 token 的详细分解、输出 token 数量、输出 token 的详细分解，以及总共使用的 token 数。  
如果使用了工具，还会输出使用的工具类型和次数，以及工具的使用详情。  
*属性  
*   
*usage.input_tokens integer  
*输入的 token 量。  
*   
*usage.input_tokens_details object  
*输入 token 的详细信息。  
  
*   
*usage.output_tokens integer  
*输出的 token 量。  
*   
*usage.output_tokens_details object  
*输出 token 的详细信息。  
  
*   
*usage.total_tokens integer  
*消耗 token 的总量。  
*   
*usage.tool_usage object  
*使用工具的信息。  
*   
*   
*usage.tool_usage_details object  
*使用工具的详细信息。  
*   
*属性  
*   
*usage.input_tokens_details.cached_tokens integer  
*缓存 token 的数量。  
*属性  
*   
*usage.output_tokens_details.reasoning_tokens integer  
*思考用 token 的数量。  
*属性  
*usage.tool_usage.image_process integer  
*调用图像处理工具的数量。  
*   
*usage.tool_usage.mcp integer  
*调用mcp工具的数量。  
*   
*usage.tool_usage.web_search integer  
*调用网络搜索工具的数量。  
*属性  
*usage.tool_usage_details.image_process object  
*调用图像处理工具的详细信息。例如：  
  
*   
*usage.tool_usage_details.mcp object  
*调用mcp工具的详细信息。例如：  
  
*   
*usage.tool_usage_details.web_search object  
*调用网络搜索工具的详细信息。例如：  
  
*  
  
属性  
  
store boolean 默认值 true  
是否存储生成的模型响应，以便后续通过 API 检索。  
false：不存储，对话内容不能被后续的 API 检索到。  
true：存储当前模型响应，对话内容能被后续的 API 检索到。  
  
caching object   
是否开启缓存。  
*属性  
*   
*caching.type string   
*取值范围：enabled， disabled。  
*enabled：开启缓存。  
*disabled：关闭缓存。  
  
属性  
  
expire_at integer/null  
存储的有效期。  
  
temperature float/null  
采样温度。  
  
context_management  object    
上下文管理响应，请求过程中应用的上下文管理策略信息。  
*策略类型  
*   
*思考块清除 object  
  
*工具调用内容清除 object  
  
*属性  
*   
*context_management.applied_edits.type string  
*上下文编辑策略类型，此处应为clear_thinking。  
*   
*context_management.applied_edits.cleared_thinking_turns integer  
*已清除的思考轮次次数。  
*属性  
*   
*context_management.applied_edits.type string  
*上下文编辑策略类型，此处应为clear_tool_uses。  
  
*context_management.applied_edits.cleared_tool_uses integer  
*已清除的工具调用次数。  
  
属性  
context_management.applied_edits array  
已应用的上下文编辑策略列表。  
策略类型  
  
六、流式响应  
当你创建 response 并将 stream 设置为 true 时，服务器会在生成 Response 的过程中，通过 Server-Sent Events（SSE）实时向客户端推送事件。本节内容介绍服务器会推送的各类事件。  
*Tips：一键展开折叠，快速检索内容  
*说明  
*打开页面右上角开关后，ctrl + f 可检索页面内所有内容。  
*   
  
Tips：一键展开折叠，快速检索内容  
  
response.created   
当响应被创建时触发的事件。  
  
response object   
创建状态的响应。包含参数与创建模型请求时，非流式调用返回的参数一致。  
  
sequence_number integer  
事件的序列号。  
  
type string  
事件的类型，总是 response.created。  
  
response.in_progress  
当响应在进程中触发的事件。  
  
response object   
进行中状态的响应。包含参数与创建模型请求时，非流式调用返回的参数一致。  
  
sequence_number integer  
事件的序列号。  
  
type string  
事件的类型，总是 response.in_progress。  
  
response.completed  
当响应已完成触发的事件。  
  
response object   
已完成状态的响应。包含参数与创建模型请求时，非流式调用返回的参数一致。  
  
sequence_number integer  
事件的序列号。  
  
type string  
事件的类型，总是 response.completed。  
  
response.failed  
当响应失败触发的事件。  
response object   
失败状态的响应。包含参数与创建模型请求时，非流式调用返回的参数一致。  
  
sequence_number integer  
事件的序列号。  
  
type string  
事件的类型，总是 response.failed。  
  
response.incomplete  
当响应以未完成状态结束时触发的事件 。  
response object   
未完成状态的响应。包含参数与创建模型请求时，非流式调用返回的参数一致。  
  
sequence_number integer  
事件的序列号。  
  
type string  
事件的类型，总是 response.incomplete。  
  
response.output_item.added  
表示添加了新的输出项。  
  
item object  
模型输出内容。  
属性  
  
文本输出 object  
增加的模型回答的内容。  
属性  
  
item.content array  
输出消息的内容。  
文本信息 object  
模型的文本输出。  
属性  
  
item.content.text string   
模型的文本输出。  
  
item.content.type string   
输出文本的类型，总是output_text。  
  
item.role  string   
输出信息的角色，总是assistant。   
  
item.status string  
输出消息的状态。  
  
item.id string  
output message 请求的唯一标识。  
  
item.type string   
输出消息的类型。  
  
内容链 object  
请求中触发了深度思考时的思维链内容。  
属性  
  
item.summary array   
推理文本内容。  
属性  
  
item.summary.text string   
模型生成答复时的推理内容。  
  
item.summary.type string   
对象的类型，总是 summary_text。  
  
item.type string   
对象的类型，此处应为 reasoning。  
  
item.status string  
该内容项的状态。  
  
item.id string  
请求的唯一标识。  
  
工具信息 object  
模型调用工具的信息  
属性  
  
item.arguments string   
要传递给函数的参数的 JSON 字符串。  
  
item.call_id string   
模型生成的函数工具调用的唯一ID。  
  
item.name string   
要运行的函数的名称。  
  
item.type string   
工具调用的类型，始终为 function_call。  
  
item.status string  
该项的状态。  
  
item.id string  
工具调用请求的唯一标识。  
  
output_index integer  
被添加的输出项的索引。  
  
sequence_number integer  
事件的序列号。  
  
type string  
事件的类型，总是response.output_item.added。  
  
response.output_item.done  
表示输出项已完成。  
item object  
已完成的输出项。  
属性  
  
文本输出 object  
增加的模型回答的内容。  
属性  
  
item.content array  
输出消息的内容。  
文本信息 object  
模型的文本输出。  
属性  
  
item.content.text string   
模型的文本输出。  
  
item.content.type string   
输出文本的类型，总是output_text。  
  
item.role  string   
输出信息的角色，总是assistant。   
  
item.status string  
输出消息的状态。  
  
item.id string  
output message 请求的唯一标识。  
  
item.type string   
输出消息的类型。  
  
内容链 object  
请求中触发了深度思考时的思维链内容。  
属性  
  
item.summary array   
推理文本内容。  
属性  
  
item.summary.text string   
模型生成答复时的推理内容。  
  
item.summary.type string   
对象的类型，总是 summary_text。  
  
item.type string   
对象的类型，此处应为 reasoning。  
  
item.status string  
该内容项的状态。  
  
item.id string  
请求的唯一标识。  
  
工具信息 object  
模型调用工具的信息  
属性  
  
item.arguments string   
要传递给函数的参数的 JSON 字符串。  
  
item.call_id string   
模型生成的函数工具调用的唯一ID。  
  
item.name string   
要运行的函数的名称。  
  
item.type string   
工具调用的类型，始终为 function_call。  
  
item.status string  
该项的状态。  
  
item.id string  
工具调用请求的唯一标识。  
  
output_index integer  
已完成的输出项的索引。  
  
sequence_number integer  
事件的序列号。  
  
type string  
事件的类型，总是 response.output_item.done。  
  
response.content_part.added  
当有新的内容部分被添加时触发。  
  
content_index integer  
内容部分的索引。  
  
item_id string  
内容部分所添加的输出项的 ID 。  
  
output_index integer  
内容部分所添加的输出项的索引 。  
  
part object  
所添加的内容部分。  
属性  
  
*输出文本 object  
*模型输出的文本对象  
  
part.textstring  
模型输出的文本内容。  
part.type string  
*output text 的类型，此处应是output_text。  
  
属性  
  
sequence_number integer  
事件的序列号。  
  
type string  
事件的类型，总是 response.content_part.added。  
  
response.content_part.done  
当内容完成时触发。  
content_index integer  
内容部分的索引。  
  
item_id string  
内容部分所添加的输出项的 ID 。  
  
output_index integer  
内容部分所添加的输出项的索引 。  
  
part object  
所完成的内容部分。  
属性  
  
*输出文本 object  
*模型输出的文本对象  
  
part.textstring  
模型输出的文本内容。  
part.type string  
*output text 的类型，此处应是output_text。  
  
属性  
  
sequence_number integer  
事件的序列号。  
  
type string  
事件的类型，总是 response.content_part.done。  
  
response.output_text.delta  
当有新增文本片段时触发。  
  
content_index integer  
增量文本所属内容块的索引。  
  
delta string  
新增的文本片段内容。  
  
item_id string  
增量文本所属输出项的唯一 ID。  
  
output_index integer  
增量文本所属输出项的列表索引。  
  
sequence_number integer  
事件的序列号。  
  
type string  
事件的类型，总是 response.output_text.delta。  
  
response.output_text.done  
文本内容完成时触发。  
content_index integer  
文本内容所属内容块的索引。  
  
item_id string  
文本内容所属输出项的唯一 ID。  
  
output_index integer  
文本内容所属输出项的列表索引。  
  
sequence_number integer  
事件的序列号。  
  
text string  
完成的文本内容。  
  
type string  
事件的类型，总是 response.output_text.done  
  
response.function_call_arguments.delta  
存在函数调用参数片段时触发。  
delta string  
本次新增的函数调用参数增量片段。  
  
item_id string  
所属输出项的唯一 ID。  
  
output_index integer  
所属输出项的列表索引。  
  
sequence_number integer  
事件的序列号。  
  
type string  
事件的类型，总是 response.function_call_arguments.delta。  
  
response.function_call_arguments.done  
当函数调用参数完成时触发。  
arguments string  
函数调用的参数。  
  
item_id string  
所属输出项的唯一 ID。  
  
output_index integer  
所属输出项的列表索引。  
  
sequence_number integer  
事件的序列号。  
  
type string  
事件的类型，总是 response.function_call_arguments.done。  
  
response.reasoning_summary_part.added  
当存在思维链新增部分时触发。  
item_id string  
所属输出项的 ID 。  
  
output_index integer  
所属输出项的索引 。  
  
summary_index integer  
输出项内，推理总结部分的子索引（若有多个总结）。  
  
part object  
所添加的内容部分。  
属性  
part.typestring  
part 的类型，总是summary_text。  
  
part.textstring  
输出的思维链文本。  
  
sequence_number integer  
事件的序列号。  
  
type string  
事件的类型，总是 response.reasoning_summary_part.added。  
  
response.reasoning_summary_part.done  
当思维链部分完成时触发。  
item_id string  
所属输出项的 ID 。  
  
output_index integer  
所属输出项的索引 。  
  
summary_index integer  
输出项内，推理总结部分的子索引（若有多个总结）。  
  
part object  
所完成的内容部分。  
属性  
part.typestring  
part 的类型，总是summary_text。  
  
part.textstring  
输出的思维链文本。  
  
sequence_number integer  
事件的序列号。  
  
type string  
事件的类型，总是 response.reasoning_summary_part.done。  
  
response.reasoning_summary_text.delta  
当存在思维链新增文本时触发。  
item_id string  
所属输出项的 ID 。  
  
output_index integer  
所属输出项的索引 。  
  
summary_index integer  
输出项内，推理总结部分的子索引（若有多个总结）。  
  
delta string  
输出的思维链文本增量片段。  
  
sequence_number integer  
事件的序列号。  
  
type string  
事件的类型，总是 response.reasoning_summary_text.delta。  
  
response.reasoning_summary_text.done  
思维链文本完成时触发。  
  
item_id string  
所属输出项的 ID 。  
  
output_index integer  
所属输出项的索引 。  
  
summary_index integer  
输出项内，推理总结部分的子索引（若有多个总结）。  
  
text string  
思维链文本完整内容。  
  
sequence_number integer  
事件的序列号。  
  
type string  
事件的类型，总是 response.reasoning_summary_text.done。  
  
error  
发生错误时触发。  
  
code string/null  
错误码。  
  
message string  
错误原因。  
  
param string/null  
错误参数。  
  
sequence_number integer  
事件的序列号。  
  
type string  
事件的类型，总是 error。  
  
