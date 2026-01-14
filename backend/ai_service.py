import os
import secrets
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
