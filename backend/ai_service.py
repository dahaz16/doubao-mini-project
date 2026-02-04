import os
import secrets
import time
from volcenginesdkarkruntime import Ark

def get_doubao_summary(text: str) -> str:
    """
    Sends the user text to Doubao AI (Ark) and returns the summary.
    """
    api_key = os.getenv("ARK_API_KEY")
    endpoint_id = os.getenv("ARK_ENDPOINT_ID")

    if not api_key or not endpoint_id:
        return "Error: ARK_API_KEY or ARK_ENDPOINT_ID not configured."

    client = Ark(api_key=api_key)

    try:
        completion = client.chat.completions.create(
            model=endpoint_id,
            messages=[
                {"role": "system", "content": "You are a helpful assistant. Please summarize the user's input concisely in Chinese."},
                {"role": "user", "content": text},
            ],
        )
        # Extract the content from the response
        return completion.choices[0].message.content
    except Exception as e:
        return f"AI Service Error: {str(e)}"

def get_doubao_chat_reply(messages: list) -> str:
    """
    Sends a list of messages to Doubao AI (Ark) and returns the reply.
    """
    api_key = os.getenv("ARK_API_KEY")
    endpoint_id = os.getenv("ARK_ENDPOINT_ID")

    if not api_key or not endpoint_id:
        return "Error: ARK_API_KEY or ARK_ENDPOINT_ID not configured."

    client = Ark(api_key=api_key)

    try:
        completion = client.chat.completions.create(
            model=endpoint_id,
            messages=messages,
        )
        return completion.choices[0].message.content
    except Exception as e:
        return f"AI Service Error: {str(e)}"

def get_doubao_chat_reply_stream(messages: list):
    """
    Sends a list of messages to Doubao AI (Ark) and YIELDS the reply chunk by chunk.
    """
    api_key = os.getenv("ARK_API_KEY")
    endpoint_id = os.getenv("ARK_ENDPOINT_ID")

    if not api_key or not endpoint_id:
        yield "Error: ARK_API_KEY or ARK_ENDPOINT_ID not configured."
        return

    client = Ark(api_key=api_key)

    try:
        stream = client.chat.completions.create(
            model=endpoint_id,
            messages=messages,
            stream=True
        )
        for chunk in stream:
            if not chunk.choices:
                continue
            content = chunk.choices[0].delta.content
            # Note: Content can be None or empty string
            if content:
                yield content
    except Exception as e:
        yield f"[AI Error: {str(e)}]"


def get_doubao_response_stream(
    input_text: str,
    previous_response_id: str = None,
    model: str = None,
    temperature: float = 0.7,
    enable_caching: bool = True
):
    """
    使用 Response API 调用豆包 LLM（流式输出）
    
    Args:
        input_text: 用户输入文本
        previous_response_id: 上一次响应 ID（用于多轮对话）
        model: 模型 ID（默认使用环境变量）
        temperature: 温度参数（0-2，默认 0.7）
        enable_caching: 是否开启缓存（默认 True）
    
    Yields:
        dict: 包含事件类型和数据的字典
            - {"type": "response_id", "response_id": "xxx"} - 响应 ID
            - {"type": "text", "content": "xxx"} - 文本片段
            - {"type": "done"} - 响应完成
            - {"type": "error", "message": "xxx"} - 错误信息
    """
    api_key = os.getenv("ARK_API_KEY")
    model = model or os.getenv("ARK_ENDPOINT_ID")
    
    if not api_key or not model:
        yield {"type": "error", "message": "ARK_API_KEY or ARK_ENDPOINT_ID not configured"}
        return
    
    # 创建客户端，设置 base_url 为 Response API 端点
    client = Ark(
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        api_key=api_key
    )
    
    try:
        # 构建请求参数
        params = {
            "model": model,
            "input": input_text,
            "temperature": temperature,
            "stream": True,
            "store": True,  # 存储上下文
            "expire_at": int(time.time()) + 3600,  # 1 小时后过期
            "thinking": {"type": "disabled"}  # 关闭思考模式（加快响应）
        }
        
        # 开启缓存
        if enable_caching:
            params["caching"] = {"type": "enabled"}
        
        # 如果有 previous_response_id，添加到参数中
        if previous_response_id:
            params["previous_response_id"] = previous_response_id
        
        # 调用 Response API
        stream = client.responses.create(**params)
        
        response_id = None
        
        # 处理流式响应
        for event in stream:
            # 从事件中获取 response_id（从 response 对象）
            if hasattr(event, 'response') and hasattr(event.response, 'id'):
                if not response_id:
                    response_id = event.response.id
                    yield {"type": "response_id", "response_id": response_id}
            
            # 获取文本内容（从 delta 属性）
            if hasattr(event, 'delta') and event.delta:
                yield {"type": "text", "content": event.delta}
        
        # 响应完成
        yield {"type": "done"}
        
    except Exception as e:
        yield {"type": "error", "message": f"Response API Error: {str(e)}"}
