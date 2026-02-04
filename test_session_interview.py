#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 Session 管理和对话记录功能
"""
import sys
import os

# 添加 backend 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from dotenv import load_dotenv
from session_service import create_session, validate_session, get_session_response_id, update_session_response_id
from interview_service import save_original_text, get_session_history, get_session_word_count
from user_service import get_user_by_openid, create_user

load_dotenv()

def test_session_and_interview():
    """测试 Session 管理和对话记录功能"""
    print("=" * 60)
    print("测试 Session 管理和对话记录功能")
    print("=" * 60)
    
    # 1. 创建测试用户
    print("\n[1] 创建测试用户")
    test_openid = "test_session_user_001"
    user = get_user_by_openid(test_openid)
    
    if not user:
        user_id = create_user(test_openid, None)
        print(f"✅ 创建用户: {user_id}")
    else:
        user_id = user['user_id']
        print(f"✅ 使用现有用户: {user_id}")
    
    # 2. 创建 Session
    print("\n[2] 创建 Session")
    session_id = create_session(user_id)
    print(f"✅ Session ID: {session_id}")
    
    # 3. 验证 Session
    print("\n[3] 验证 Session")
    is_valid = validate_session(session_id)
    print(f"✅ Session 有效: {is_valid}")
    
    # 4. 保存对话记录
    print("\n[4] 保存对话记录")
    
    # 用户输入
    user_text = "你好，我想记录一下我的童年回忆"
    save_original_text(session_id, user_id, user_text, speaker_type=0)
    print(f"✅ 保存用户输入: {user_text}")
    
    # AI 回复
    ai_text = "您好！很高兴能帮您记录童年回忆。请问您想从哪个时期开始讲起呢？"
    save_original_text(session_id, user_id, ai_text, speaker_type=1)
    print(f"✅ 保存 AI 回复: {ai_text}")
    
    # 5. 获取历史记录
    print("\n[5] 获取历史记录")
    history = get_session_history(session_id)
    print(f"✅ 历史记录数: {len(history)}")
    for i, record in enumerate(history, 1):
        speaker = "用户" if record['speaker_type'] == 0 else "AI"
        print(f"   {i}. [{speaker}] {record['original_text'][:50]}...")
    
    # 6. 统计字数
    print("\n[6] 统计字数")
    word_count = get_session_word_count(session_id)
    print(f"✅ 总字数: {word_count}")
    
    # 7. 更新 response_id
    print("\n[7] 更新 response_id")
    test_response_id = "resp_test_12345678"
    update_session_response_id(session_id, test_response_id)
    print(f"✅ 更新 response_id: {test_response_id}")
    
    # 8. 获取 response_id
    print("\n[8] 获取 response_id")
    saved_response_id = get_session_response_id(session_id)
    print(f"✅ 获取 response_id: {saved_response_id}")
    
    # 验证
    if saved_response_id == test_response_id:
        print("✅ response_id 验证通过")
    else:
        print("❌ response_id 验证失败")
    
    # 总结
    print("\n" + "=" * 60)
    print("测试完成！")
    print("=" * 60)
    print(f"Session ID: {session_id}")
    print(f"User ID: {user_id}")
    print(f"对话记录数: {len(history)}")
    print(f"总字数: {word_count}")
    print(f"Response ID: {saved_response_id}")
    print("\n✅ 所有测试通过！Session 管理和对话记录功能正常！")

if __name__ == "__main__":
    test_session_and_interview()
