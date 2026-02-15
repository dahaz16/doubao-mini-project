# 豆包AI CoT标记泄露问题报告

## 问题概述

在使用豆包AI的Responses API进行流式对话时，LLM的输出中出现了**内部思考标记（CoT Markers）泄露**到最终用户可见的文本中。

## 问题表现

### 乱码示例

以下是从数据库中提取的实际AI回复内容，包含了不应该暴露给用户的内部标记：

1. **SILENT标记泄露**：
```
这份"爱<[SILENT_never_used_51bce0c785ca2f68081bfa7d91973934]>这份"爱咋想咋想"的松弛感真的太难得啦。
```

2. **think标记泄露**：
```
你说的 Pauline</think_never_used_51bce0c785ca2f68081bfa7d91973934>你说的这点特别实在。
```

3. **重复内容 + 标记**：
```
哈哈，<[SILENT_never_used_51bce0c785ca2f68081bfa7d91973934]>哈哈，这种"顺势而为"的应对方式真的很从容。
```

### 统计数据

- 检查了10条最近的AI回复
- **9条包含CoT标记泄露**（90%的失败率）
- 主要标记类型：
  - `<[SILENT_never_used_51bce0c785ca2f68081bfa7d91973934]>`
  - `</think_never_used_51bce0c785ca2f68081bfa7d91973934>`

## API调用详情

### 1. 请求参数

我们使用的是**Responses API的流式调用**，具体参数如下：

```python
params = {
    "model": "ep-20250128165659-xbqvd",  # 豆包Pro模型endpoint
    "input": [
        {
            "role": "system",
            "content": "你是念念，一个温暖、善解人意的AI访谈员..."  # System Prompt
        },
        {
            "role": "user",
            "content": "ot:用户输入的文本;hc:导演提示内容"  # 用户消息
        }
    ],
    "temperature": 1.0,
    "stream": True,  # 流式输出
    "store": True,  # 启用Session存储
    "expire_at": 1739519121,  # Unix时间戳
    "thinking": {"type": "disabled"},  # 明确禁用thinking模式
    "extra_body": {"caching": {"type": "enabled"}},  # 启用Session Caching
    "previous_response_id": "resp-xxx..."  # 上一轮的response_id（延续Session）
}
```

**关键配置**：
- `thinking`: `{"type": "disabled"}` - **已明确禁用深度思考模式**
- `stream`: `True` - 流式输出
- Session Caching已启用

### 2. API调用代码

```python
from volcenginesdkarkruntime import AsyncArk

client = AsyncArk(
    base_url="https://ark.cn-beijing.volces.com/api/v3",
    api_key="YOUR_API_KEY"
)

stream = await client.responses.create(**params)

async for event in stream:
    delta = getattr(event, 'delta', None)
    if delta:
        # delta中包含了CoT标记！
        print(delta)  # 输出: "哈哈，<[SILENT_never_used_51bce0c785ca2f68081bfa7d91973934]>哈哈，..."
```

### 3. 实际返回的流式数据

在流式输出中，我们收到的`delta`（文本增量）包含了这些标记：

```
delta_1: "这份"
delta_2: "爱"
delta_3: "<[SILENT_never_used_51bce0c785ca2f68081bfa7d91973934]>"  # ❌ 不应该出现
delta_4: "这份"
delta_5: ""爱咋想咋想"的松弛感..."
```

## 问题分析

### 1. 标记格式分析

观察到的标记格式：
- `<[SILENT_never_used_{32位十六进制hash}]>`
- `</think_never_used_{32位十六进制hash}>`
- `<think_never_used_{32位十六进制hash}>`

这些标记看起来是模型内部用于标记**思考过程**的特殊token，类似于：
- `<[SILENT_...]>` - 可能用于标记"静默思考"的内容
- `<think_...>` / `</think_...>` - 可能用于包裹思考过程

### 2. 可能的原因

1. **模型配置问题**：
   - 虽然我们设置了`"thinking": {"type": "disabled"}`，但模型仍然在内部使用CoT
   - 可能是某个prompt或系统配置触发了CoT模式

2. **API过滤失效**：
   - API应该在返回前过滤这些内部标记
   - 但过滤机制可能失效或不完整

3. **Session Caching副作用**：
   - 使用Session Caching时，可能缓存了包含CoT标记的中间状态
   - 导致后续请求也继续输出这些标记

## 环境信息

- **SDK版本**: `volcenginesdkarkruntime` (最新版本)
- **API端点**: `https://ark.cn-beijing.volces.com/api/v3`
- **模型**: 豆包Pro (endpoint: `ep-20250128165659-xbqvd`)
- **调用方式**: Responses API (流式)
- **Session Caching**: 已启用
- **Thinking模式**: 已明确禁用

## 影响范围

- **用户体验**: 用户看到乱码，严重影响对话质量
- **数据污染**: 这些标记被保存到数据库中，污染了历史记录
- **TTS合成**: 如果这些标记被送入TTS，可能导致语音合成失败或产生异常音频

## 期望行为

1. **API应该自动过滤**：Responses API在返回流式数据前，应该自动过滤所有内部标记
2. **Thinking禁用生效**：当设置`"thinking": {"type": "disabled"}`时，不应该产生任何思考标记
3. **干净的输出**：用户应该只看到最终的回复文本，不包含任何内部标记

## 临时解决方案

我们目前在应用层添加了正则表达式过滤：

```python
import re

def filter_cot_markers(text: str) -> str:
    """过滤CoT标记"""
    cot_patterns = [
        r'<\[SILENT_never_used_[a-f0-9]+\]>',
        r'</think_never_used_[a-f0-9]+>',
        r'<think_never_used_[a-f0-9]+>',
    ]
    
    for pattern in cot_patterns:
        text = re.sub(pattern, '', text)
    
    return text
```

但这只是**临时方案**，我们希望API层面能够解决这个问题。

## 请求支持

1. **确认问题**：请确认这是否是已知问题
2. **根本原因**：请说明为什么会出现CoT标记泄露
3. **修复计划**：是否有计划在API层面修复此问题
4. **配置建议**：是否有其他参数配置可以避免此问题

## 附加信息

如需更多信息（如完整的请求/响应日志、数据库截图等），请告知，我们可以提供。

---

**报告时间**: 2026-02-14  
**用户ID**: 32826937-85e6-46cb-812b-e5632fffa5a6  
**联系方式**: [您的联系方式]
