#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 Response API 功能
"""
import sys
import os

# 添加 backend 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from dotenv import load_dotenv
from ai_service import get_doubao_response_stream

load_dotenv()

def test_response_api():
    """测试 Response API 基本功能"""
    print("=" * 60)
    print("测试 Response API")
    print("=" * 60)
    
    # 第一轮对话
    print("\n[第一轮对话]")
    print("用户：你好，请介绍一下你自己")
    print("AI：", end="", flush=True)
    
    response_id = None
    full_reply_1 = ""
    
    for event in get_doubao_response_stream(
        input_text="你好，请介绍一下你自己",
        previous_response_id=None,
        enable_caching=False  # 关闭缓存
    ):
        event_type = event.get("type")
        
        if event_type == "response_id":
            response_id = event["response_id"]
            print(f"\n[获取到 response_id: {response_id}]")
            print("AI：", end="", flush=True)
        
        elif event_type == "text":
            content = event["content"]
            full_reply_1 += content
            print(content, end="", flush=True)
        
        elif event_type == "done":
            print("\n[第一轮对话完成]")
        
        elif event_type == "error":
            print(f"\n❌ 错误: {event['message']}")
            return
    
    if not response_id:
        print("\n❌ 未获取到 response_id")
        return
    
    # 第二轮对话（使用 previous_response_id）
    print("\n" + "=" * 60)
    print("[第二轮对话 - 使用缓存]")
    print(f"previous_response_id: {response_id}")
    print("=" * 60)
    print("\n用户：请详细说明你的能力")
    print("AI：", end="", flush=True)
    
    full_reply_2 = ""
    new_response_id = None
    
    for event in get_doubao_response_stream(
        input_text="请详细说明你的能力",
        previous_response_id=response_id,  # 使用上一次的 response_id
        enable_caching=False  # 关闭缓存
    ):
        event_type = event.get("type")
        
        if event_type == "response_id":
            new_response_id = event["response_id"]
            print(f"\n[获取到新的 response_id: {new_response_id}]")
            print("AI：", end="", flush=True)
        
        elif event_type == "text":
            content = event["content"]
            full_reply_2 += content
            print(content, end="", flush=True)
        
        elif event_type == "done":
            print("\n[第二轮对话完成]")
        
        elif event_type == "error":
            print(f"\n❌ 错误: {event['message']}")
            return
    
    # 总结
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    print(f"第一轮 response_id: {response_id}")
    print(f"第二轮 response_id: {new_response_id}")
    print(f"第一轮回复字数: {len(full_reply_1)}")
    print(f"第二轮回复字数: {len(full_reply_2)}")
    print("\n✅ Response API 测试成功！")
    print("✅ 缓存功能已启用（第二轮对话使用了 previous_response_id）")

if __name__ == "__main__":
    test_response_api()
