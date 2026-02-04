#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证 Dir Agent 完整流程的脚本
模拟从对话产生到速记员处理，再到导演产出建议的链路。
"""
import sys
import os
import asyncio
import logging

# 将 backend 目录加入路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from stn_service import run_stn_agent_async
from stn_database import get_latest_hint, get_previous_dialogues
import time

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

async def test_full_pipeline():
    # 使用真实的 user_id 避免外键约束错误
    user_id = 'ed23d507-59f0-4ac7-bdbf-ed8fd62784d9'
    session_id = 'b0eebc99-9c0b-4ef8-bb6d-6bb9bd380a12'
    
    # 模拟一段对话
    dialogue = "U: 我小时候住在上海的一个老弄堂里。I: 那弄堂里有什么特别的回忆吗？U: 有一个很大的防空洞，我们经常去那里探险。里面黑漆漆的，非常刺激。"
    cache_pool_id = 999999 # 模拟 ID
    
    logging.info("Step 1: 触发 Stn Agent 处理对话...")
    # 这里我们直接调用 stn_service 中的逻辑
    from stn_service import process_dialogue_to_structure
    await process_dialogue_to_structure(user_id, session_id, dialogue, cache_pool_id)
    
    logging.info("Step 2: 等待异步任务完成 (Stn -> Dir)...")
    await asyncio.sleep(10) # 留出足够时间给 LLM
    
    logging.info("Step 3: 检查数据库结果...")
    hint = get_latest_hint(user_id)
    if hint:
        logging.info(f"✅ 成功获取导演建议: {hint}")
    else:
        logging.error("❌ 未能在 hint_board 中找到建议。")
    
    logging.info("Step 4: 测试 pc (前情提要) 组装...")
    pc = get_previous_dialogues(user_id, limit=3)
    logging.info(f"对话历史 (pc): {pc}")

if __name__ == "__main__":
    asyncio.run(test_full_pipeline())
