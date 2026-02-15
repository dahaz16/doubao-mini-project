#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
Intv Service (访谈员 Agent 服务) v3.3
============================================================================

访谈员 Agent 完整工作流：
1. 接收用户输入
2. 存储原始文本 (interview_original_text)
3. 更新缓存池，判断是否触发 Stn
4. Session 处理（新建/复用逻辑）
5. 获取最新 Hintboard 更新
6. 构建 LLM 输入
7. 调用 Intv LLM（流式）
8. 存储回复，更新 narration_status

根据《服务端流程文档与数据库结构设计 v3.3》实现。
"""

import asyncio
import logging
import time
import uuid
from datetime import datetime, timezone, timedelta
from typing import Dict, Any, Optional, Generator, AsyncGenerator

from .database import get_db_connection
from .narration_service import (
    get_or_create_narration_status,
    check_intv_session_valid,
    update_intv_session,
    append_cachepool,
    check_cachepool_threshold,
    get_intv_previous_content,
    check_hint_updated,
)
from .llm_api_service import call_intv_llm_stream
from .config_manager import get_config, get_active_prompt

logging.basicConfig(level=logging.INFO)


# ============================================================================
# v3.4: Intv System Prompt 现已从 prompt_config 表动态读取
# ============================================================================


# ============================================================================
# 存储原始文本
# ============================================================================

def save_interview_text(
    user_id: str,
    speaker_type: int,
    text: str,
    has_voice: bool = False
) -> Optional[int]:
    """
    存储采访原始文本
    
    speaker_type: 0=用户, 1=AI
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO interview_original_text 
                    (user_id, speaker_type, has_voice, original_text)
                    VALUES (%s, %s, %s, %s)
                    RETURNING interview_original_text_id
                """, (user_id, speaker_type, has_voice, text))
                text_id = cursor.fetchone()[0]
                conn.commit()
                return text_id
    except Exception as e:
        logging.error(f"❌ 存储原始文本失败: {e}")
        return None


def _get_current_session_id(user_id: str) -> str:
    """获取当前 Intv 的 Session ID"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT intv_llm_session_id
                    FROM narration_status
                    WHERE user_id = %s
                """, (user_id,))
                result = cursor.fetchone()
                return result[0] if result and result[0] else str(uuid.uuid4())
    except Exception as e:
        logging.error(f"❌ 获取 Session ID 失败: {e}")
        return str(uuid.uuid4())


# ============================================================================
# Intv Agent 流式响应
# ============================================================================

async def process_user_input(
    user_id: str,
    user_text: str,
    has_voice: bool = False
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    处理用户输入并流式返回 AI 响应
    
    Yields:
        dict:
            - {"type": "start"}
            - {"type": "text", "content": "xxx"}
            - {"type": "done", "full_text": "xxx"}
            - {"type": "error", "message": "xxx"}
    """
    logging.info(f"🎤 Intv 处理输入: user={user_id[:8]}..., text={user_text[:50]}...")
    
    try:
        # Step 0: 获取或生成 Session ID (v3.3 逻辑)
        session_id = _get_current_session_id(user_id)
        yield {"type": "session_id", "session_id": session_id}

        # Step 1: 存储用户输入
        user_text_id = save_interview_text(user_id, speaker_type=0, text=user_text, has_voice=has_voice)
        yield {"type": "user_text_id", "text_id": user_text_id}
        
        # Step 1.5: 如果是语音输入,记录 ASR 调用
        if has_voice and user_text_id:
            try:
                from db_logger import log_asr_call
                
                # 获取 ASR 模型ID (火山 ASR, ID=2)
                model_id = 2  # 根据之前查询的结果,火山 ASR 的 ID 是 2
                
                # 估算耗时和成本 (这里使用估算值,实际应该在 ASR 调用时记录)
                # 假设平均每秒音频需要 100ms 处理时间,按字数估算音频时长
                estimated_audio_seconds = len(user_text) / 3  # 假设每秒说 3 个字
                duration_ms = int(estimated_audio_seconds * 100)  # 估算处理耗时
                cost = estimated_audio_seconds * 0.001  # 示例:每秒 0.001 元
                
                log_asr_call(user_id, user_text_id, model_id, duration_ms, cost)
            except Exception as e:
                logging.error(f"记录 ASR 调用失败: {e}")
        
        # Step 2: 更新缓存池
        append_cachepool(user_id, "U", user_text)
        
        # Step 3: 检查是否触发 Stn
        should_trigger, current_len = check_cachepool_threshold(user_id)
        if should_trigger:
            asyncio.create_task(_trigger_stn_agent(user_id))
        
        # Step 4: Session 处理
        session_valid, reason = check_intv_session_valid(user_id)
        status = get_or_create_narration_status(user_id)
        
        if session_valid:
            # Session 有效：复用
            prev_resp_id = status.get('intv_llm_session_previous_response_id')
            prev_content = status.get('intv_llm_previous_content') or ''
            logging.info(f"🎤 Intv Session 有效，复用 prev_resp_id")
        else:
            # Session 无效：新建
            prev_resp_id = None
            prev_content = get_intv_previous_content(user_id)
            
            # 重置 Session
            update_intv_session(user_id, reset=True)
            logging.info(f"🎤 Intv Session 无效 ({reason})，新建 Session")
        
        # Step 5: 检查 Hintboard 更新
        hint_updated, new_hint_id, new_hint_content = check_hint_updated(user_id)
        hint_content = new_hint_content if hint_updated else ''
        
        if hint_updated:
            update_intv_session(user_id, hint_id=new_hint_id)
            logging.info(f"🎤 检测到 Hint 更新: {new_hint_id}")
        
        # Step 6: 构建 LLM 输入
        is_new_session = not session_valid
        llm_input = _build_intv_input(
            is_new_session=is_new_session,
            previous_content=prev_content,
            current_input=user_text,
            hint_content=hint_content
        )
        
        # Step 7: 调用 Intv LLM（流式）
        yield {"type": "start"}
        
        full_response = ""
        new_response_id = None
        
        # 序列化 llm_input 为字符串（用于记录）
        import json
        llm_input_str = json.dumps(llm_input, ensure_ascii=False)
        
        async for event in call_intv_llm_stream(
            user_id=user_id,
            input_messages=llm_input,
            previous_response_id=prev_resp_id,
            llm_input_str=llm_input_str,
            related_original_text_id=user_text_id
        ):
            event_type = event.get("type")
            
            if event_type == "response_id":
                new_response_id = event.get("response_id")
            
            elif event_type == "text":
                content = event.get("content", "")
                full_response += content
                yield {"type": "text", "content": content}
            
            elif event_type == "error":
                yield {"type": "error", "message": event.get("message")}
                return
            
            elif event_type == "done":
                pass  # 继续处理
        
        # Step 8: 存储 AI 回复
        ai_text_id = save_interview_text(user_id, speaker_type=1, text=full_response, has_voice=True)
        
        # Step 9: 更新缓存池（AI 回复）
        append_cachepool(user_id, "I", full_response)
        
        # ✅ v3.9 Fix: 移除 AI 回复后的重复检查
        # 原因：用户输入后已经检查过一次，AI 回复后再检查会导致短时间内重复触发 Stn Agent
        # 因为用户输入和 AI 回复都会累积到缓存池，所以只需在用户输入后检查一次即可
        
        # Step 10: 更新 Intv Session 状态
        word_count = len(user_text) + len(full_response)
        update_intv_session(
            user_id=user_id,
            session_id=new_response_id,
            previous_response_id=new_response_id,
            word_count_delta=word_count,
            previous_content=_format_dialogue_history(prev_content, user_text, full_response)
        )
        
        yield {"type": "done", "full_text": full_response, "ai_text_id": ai_text_id}
        
        logging.info(f"✅ Intv 响应完成: {len(full_response)} 字符")
        
    except Exception as e:
        logging.error(f"❌ Intv 处理异常: {e}", exc_info=True)
        yield {"type": "error", "message": str(e)}


# ============================================================================
# 构建 LLM 输入
# ============================================================================

def _build_intv_input(
    is_new_session: bool,
    previous_content: str,
    current_input: str,
    hint_content: str
) -> list:
    """
    构建 Intv LLM 输入（v3.4）
    
    根据 session 是否新建，构造不同的 input 数组：
    - 新建 session: [{role: system, content: prompt}, {role: assistant, content: "pc:..."}, {role: user, content: "ot:...;hc:..."}]
    - 未新建: [{role: user, content: "ot:...;hc:..."}]
    """
    # 获取 prompt
    intv_prompt = get_active_prompt(llm_type=0)
    if not intv_prompt:
        logging.warning("⚠️ 未找到 intv prompt，使用空字符串")
        intv_prompt = ""
    
    # 构建当前 user 消息
    user_parts = [f"ot:{current_input}"]
    if hint_content:
        user_parts.append(f"hc:{hint_content}")
    user_message = ";".join(user_parts)
    
    if is_new_session:
        # 新建 session
        messages = [{"role": "system", "content": intv_prompt}]
        
        if previous_content:
            messages.append({"role": "assistant", "content": f"pc:{previous_content}"})
        
        messages.append({"role": "user", "content": user_message})
        return messages
    else:
        # 未新建 session
        return [{"role": "user", "content": user_message}]


def _format_dialogue_history(prev_content: str, user_text: str, ai_response: str) -> str:
    """
    格式化对话历史，用于存储到 intv_llm_previous_content
    
    保留最近几轮对话
    """
    new_round = f"U:{user_text} I:{ai_response}"
    
    if prev_content:
        # 限制长度，保留最近 5000 字符
        combined = f"{prev_content} {new_round}"
        if len(combined) > 5000:
            combined = combined[-5000:]
        return combined
    
    return new_round


# ============================================================================
# 触发 Stn Agent
# ============================================================================

async def _trigger_stn_agent(user_id: str):
    """异步触发 Stn Agent"""
    try:
        # 动态导入避免循环依赖
        from .stn_service import run_stn_agent
        await run_stn_agent(user_id)
    except Exception as e:
        logging.error(f"❌ 触发 Stn Agent 失败: {e}")


# ============================================================================
# 同步版本（用于非异步环境）
# ============================================================================

def process_user_input_sync(
    user_id: str,
    user_text: str,
    has_voice: bool = False
) -> Generator[Dict[str, Any], None, None]:
    """
    同步版本的用户输入处理
    
    用于不支持 async 的环境
    """
    import asyncio
    
    async def _async_wrapper():
        results = []
        async for event in process_user_input(user_id, user_text, has_voice):
            results.append(event)
        return results
    
    # 使用事件循环运行异步函数
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    results = loop.run_until_complete(_async_wrapper())
    for result in results:
        yield result
