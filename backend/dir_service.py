#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
Dir Service (导演 Agent 服务) v3.3
============================================================================

导演 Agent 完整工作流：
1. 并发控制：用户级 FIFO 队列
2. Session 处理：检查有效性，决定上下文模式
3. 获取待处理的 Storyboard
4. 调用 Dir LLM
5. 写入 Hintboard
6. 更新 Storyboard 处理状态

根据《服务端流程文档与数据库结构设计 v3.3》实现。
"""

import asyncio
import logging
from typing import Dict, Any, Optional

from .narration_service import (
    get_or_create_narration_status,
    check_dir_session_valid,
    update_dir_session,
    insert_hint,
)
from .llm_api_service import call_dir_llm
from .stn_database import (
    get_unprocessed_storyboards_for_dir,
    get_latest_storyboards,
    mark_storyboards_dir_processed,
    format_storyboards_for_llm,
)
from .config_manager import get_config, get_active_prompt

logging.basicConfig(level=logging.INFO)


# ============================================================================
# 用户级并发控制（FIFO 队列）
# ============================================================================

_user_locks: Dict[str, asyncio.Lock] = {}


def _get_user_lock(user_id: str) -> asyncio.Lock:
    """获取用户级别的锁"""
    if user_id not in _user_locks:
        _user_locks[user_id] = asyncio.Lock()
    return _user_locks[user_id]


# ============================================================================
# v3.4: Dir System Prompt 现已从 prompt_config 表动态读取
# ============================================================================


# ============================================================================
# Dir Agent 主入口
# ============================================================================

async def run_dir_agent(user_id: str) -> bool:
    """
    运行 Dir Agent
    
    这是一个异步函数，由 Stn Agent 完成后触发。
    使用用户级锁保证同一用户的任务按 FIFO 顺序执行。
    
    Returns:
        bool: 是否成功
    """
    lock = _get_user_lock(user_id)
    
    async with lock:
        logging.info(f"🎬 Dir Agent 开始工作 (User: {user_id[:8]}...)")
        
        try:
            # Step 1: 检查 Session 有效性
            session_valid, reason = check_dir_session_valid(user_id)
            
            # Step 2: 获取 Storyboard 内容
            if session_valid:
                # 有效时：获取 dir_processed_status=0 的记录
                sb_records, max_dir_read_id = get_unprocessed_storyboards_for_dir(user_id)
                
                if not sb_records:
                    logging.info("🎬 Dir Agent: 没有新的 Storyboard 需要处理")
                    return True
                
                logging.info(f"🎬 Dir Session 有效，获取 {len(sb_records)} 条未处理 SB")
            else:
                # 无效时：获取最新 N 条作为完整上下文
                sb_records = get_latest_storyboards(user_id)
                max_dir_read_id = max(sb['story_id'] for sb in sb_records) if sb_records else None
                
                if not sb_records:
                    logging.info("🎬 Dir Agent: 没有 Storyboard 记录")
                    return True
                
                logging.info(f"🎬 Dir Session 无效 ({reason})，获取 {len(sb_records)} 条最新 SB")
            
            sb_context = format_storyboards_for_llm(sb_records)
            
            # Step 3: 获取当前 Dir Session 状态
            status = get_or_create_narration_status(user_id)
            prev_response_id = status.get('dir_llm_session_previous_response_id') if session_valid else None
            
            # Step 4: 构建 LLM 输入
            is_new_session = not session_valid
            llm_input = _build_dir_input(sb_context, is_new_session)
            
            # 序列化 llm_input 为字符串（用于记录）
            import json
            llm_input_str = json.dumps(llm_input, ensure_ascii=False)
            
            # Step 5: 调用 Dir LLM (Async)
            result = await call_dir_llm(
                user_id=user_id,
                input_messages=llm_input,
                previous_response_id=prev_response_id,
                llm_input_str=llm_input_str
            )
            
            if not result.get('success'):
                logging.error(f"❌ Dir LLM 调用失败: {result.get('error')}")
                return False
            
            hint_content = result.get('content', '').strip()
            new_response_id = result.get('response_id')
            
            if not hint_content:
                logging.warning("⚠️ Dir LLM 返回空内容")
                return True
            
            # Step 6: 写入 Hintboard
            hint_id = insert_hint(user_id, hint_content)
            
            # Step 7: 更新 Dir Session 状态
            word_count = len(hint_content)
            update_dir_session(
                user_id=user_id,
                session_id=new_response_id,
                previous_response_id=new_response_id,
                word_count_delta=word_count
            )
            
            # Step 8: 标记 Storyboard 已处理
            if max_dir_read_id:
                mark_storyboards_dir_processed(user_id, max_dir_read_id)
            
            logging.info(f"✅ Dir Agent 完成: hint_id={hint_id}, content={hint_content[:50]}...")
            return True
            
        except Exception as e:
            logging.error(f"❌ Dir Agent 异常: {e}", exc_info=True)
            return False


# ============================================================================
# 构建 LLM 输入
# ============================================================================

def _build_dir_input(sb_context: str, is_new_session: bool) -> list:
    """
    构建 Dir LLM 输入（v3.4）
    
    根据 session 是否新建，构造不同的 input 数组：
    - 新建 session: [{role: system, content: prompt}, {role: user, content: sb:...}]
    - 未新建: [{role: user, content: sb:...
}]
    """
    # 获取 prompt
    dir_prompt = get_active_prompt(llm_type=2)
    if not dir_prompt:
        logging.warning("⚠️ 未找到 dir prompt，使用空字符串")
        dir_prompt = ""
    
    user_message = sb_context
    
    if is_new_session:
        return [
            {"role": "system", "content": dir_prompt},
            {"role": "user", "content": user_message}
        ]
    else:
        return [{"role": "user", "content": user_message}]
