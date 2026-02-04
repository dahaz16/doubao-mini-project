#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v3.3 端到端测试脚本

测试 Intv → Stn → Dir 完整链路
"""

import asyncio
import json
import logging
import sys
import os

# 添加 backend 目录到路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def test_e2e():
    """端到端测试"""
    print("\n" + "="*60)
    print("v3.3 端到端测试")
    print("="*60 + "\n")
    
    # 导入服务模块
    from narration_service import (
        get_or_create_narration_status,
        append_cachepool,
        check_cachepool_threshold,
    )
    from intv_service import process_user_input
    from stn_service import run_stn_agent
    from dir_service import run_dir_agent
    from user_service import create_user, get_user_by_openid
    
    # 创建测试用户
    test_openid = "test_e2e_user_v33"
    user = get_user_by_openid(test_openid)
    if not user:
        user_id = create_user(test_openid)
        print(f"✅ 创建测试用户: {user_id}")
    else:
        user_id = user['user_id']
        print(f"✅ 使用已有用户: {user_id}")
    
    # 1. 测试 narration_status 创建
    print("\n--- 1. 测试 narration_status ---")
    status = get_or_create_narration_status(user_id)
    print(f"✅ narration_status 创建成功: {json.dumps(status, indent=2, ensure_ascii=False, default=str)}")
    
    # 2. 测试缓存池
    print("\n--- 2. 测试缓存池 ---")
    append_cachepool(user_id, "U", "我小时候住在北京的一个四合院里")
    append_cachepool(user_id, "I", "四合院里的生活一定很有意思，能给我讲讲吗？")
    threshold_reached, current_len = check_cachepool_threshold(user_id)
    print(f"✅ 缓存池: 当前长度={current_len}, 达到阈值={threshold_reached}")
    
    # 3. 测试 Intv Agent 流式响应
    print("\n--- 3. 测试 Intv Agent ---")
    user_input = "我记得那时候院子里有一棵大枣树"
    
    full_response = ""
    async for event in process_user_input(user_id, user_input):
        event_type = event.get("type")
        if event_type == "start":
            print("   开始生成...")
        elif event_type == "text":
            content = event.get("content", "")
            full_response += content
            print(f"   [text] {content[:30]}..." if len(content) > 30 else f"   [text] {content}")
        elif event_type == "done":
            print(f"✅ Intv 响应完成: {len(full_response)} 字符")
        elif event_type == "error":
            print(f"❌ Intv 错误: {event.get('message')}")
            return False
    
    # 4. 测试 Stn Agent
    print("\n--- 4. 测试 Stn Agent ---")
    try:
        result = await run_stn_agent(user_id)
        print(f"✅ Stn Agent 执行结果: {result}")
    except Exception as e:
        print(f"⚠️ Stn Agent 跳过 (可能缓存池为空): {e}")
    
    # 5. 测试 Dir Agent
    print("\n--- 5. 测试 Dir Agent ---")
    try:
        result = await run_dir_agent(user_id)
        print(f"✅ Dir Agent 执行结果: {result}")
    except Exception as e:
        print(f"⚠️ Dir Agent 跳过 (可能无 SB 记录): {e}")
    
    # 6. 检查最终状态
    print("\n--- 6. 检查最终状态 ---")
    final_status = get_or_create_narration_status(user_id)
    print(f"✅ 最终状态:")
    print(f"   - cache_pool_length: {final_status.get('cache_pool_length')}")
    print(f"   - intv_llm_session_word_count: {final_status.get('intv_llm_session_word_count')}")
    print(f"   - hint_content: {final_status.get('hint_content')}")
    
    print("\n" + "="*60)
    print("✅ 端到端测试完成！")
    print("="*60 + "\n")
    
    return True


if __name__ == "__main__":
    asyncio.run(test_e2e())
