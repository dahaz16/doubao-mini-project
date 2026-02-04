#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Debug 日志服务
提供管理后台查询用户完整 debug 信息的功能
"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime, timedelta
from .database import get_db_connection

logging.basicConfig(level=logging.INFO)


def get_user_debug_logs(
    user_id: str,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None
) -> Dict[str, Any]:
    """
    获取用户的完整 debug 日志
    
    Args:
        user_id: 用户ID
        start_time: 开始时间(默认为 24 小时前)
        end_time: 结束时间(默认为当前时间)
    
    Returns:
        {
            "user_id": "xxx",
            "narration_status": {...},
            "active_prompts": {...},
            "logs": [...]
        }
    """
    # 默认查询最近 24 小时
    if not end_time:
        end_time = datetime.now()
    if not start_time:
        start_time = end_time - timedelta(hours=24)
    
    logging.info(f"🔍 获取用户 debug 日志: user_id={user_id[:8]}..., time_range={start_time} ~ {end_time}")
    
    # 1. 获取 narration_status
    narration_status = _get_narration_status(user_id)
    
    # 2. 获取当前激活的 prompts
    active_prompts = _get_active_prompts()
    
    # 3. 聚合时间线日志
    logs = _aggregate_logs(user_id, start_time, end_time)
    
    return {
        "user_id": user_id,
        "narration_status": narration_status,
        "active_prompts": active_prompts,
        "logs": logs
    }


def _get_narration_status(user_id: str) -> Optional[Dict[str, Any]]:
    """获取 narration_status 完整状态"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        intv_llm_session_id,
                        intv_llm_session_word_count,
                        intv_llm_session_expire_at,
                        intv_llm_session_previous_response_id,
                        intv_llm_previous_content,
                        intv_llm_hint_id,
                        stn_llm_session_id,
                        stn_llm_session_word_count,
                        stn_llm_session_expire_at,
                        stn_llm_session_previous_response_id,
                        stn_unprocessed_content,
                        dir_llm_session_id,
                        dir_llm_session_word_count,
                        dir_llm_session_expire_at,
                        dir_llm_session_previous_response_id,
                        chat_cachepool_content
                    FROM narration_status
                    WHERE user_id = %s
                """, (user_id,))
                
                row = cursor.fetchone()
                if not row:
                    return None
                
                return {
                    "intv_llm_session_id": str(row[0]) if row[0] else None,
                    "intv_llm_session_word_count": row[1] or 0,
                    "intv_llm_session_expire_at": row[2].isoformat() if row[2] else None,
                    "intv_llm_session_previous_response_id": row[3],
                    "intv_llm_previous_content": row[4],
                    "intv_llm_hint_id": row[5],
                    "stn_llm_session_id": str(row[6]) if row[6] else None,
                    "stn_llm_session_word_count": row[7] or 0,
                    "stn_llm_session_expire_at": row[8].isoformat() if row[8] else None,
                    "stn_llm_session_previous_response_id": row[9],
                    "stn_unprocessed_content": row[10],
                    "dir_llm_session_id": str(row[11]) if row[11] else None,
                    "dir_llm_session_word_count": row[12] or 0,
                    "dir_llm_session_expire_at": row[13].isoformat() if row[13] else None,
                    "dir_llm_session_previous_response_id": row[14],
                    "chat_cachepool_content": row[15]
                }
    except Exception as e:
        logging.error(f"❌ 获取 narration_status 失败: {e}")
        return None


def _get_active_prompts() -> Dict[str, Any]:
    """获取当前激活的 prompts"""
    prompts = {
        "intv": None,
        "stn": None,
        "dir": None
    }
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # 查询三个 Agent 的激活 prompt
                for agent_name, llm_type in [("intv", 0), ("stn", 1), ("dir", 2)]:
                    cursor.execute("""
                        SELECT prompt_id, prompt_content, remark
                        FROM prompt_config
                        WHERE llm_type = %s AND is_active = TRUE
                        ORDER BY prompt_id DESC
                        LIMIT 1
                    """, (llm_type,))
                    
                    row = cursor.fetchone()
                    if row:
                        prompts[agent_name] = {
                            "prompt_id": row[0],
                            "content": row[1],
                            "remark": row[2]
                        }
    except Exception as e:
        logging.error(f"❌ 获取 active_prompts 失败: {e}")
    
    return prompts


def _aggregate_logs(user_id: str, start_time: datetime, end_time: datetime) -> List[Dict[str, Any]]:
    """
    聚合时间线日志
    
    合并以下数据源:
    1. interview_original_text - 用户输入和 AI 输出
    2. llm_processed - LLM 调用记录
    3. asr_processed - ASR 调用记录
    4. tts_processed - TTS 调用记录
    5. interview_original_voice - 音频链接
    """
    logs = []
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # 1. 获取用户名
                cursor.execute("SELECT user_name FROM users WHERE user_id = %s", (user_id,))
                user_row = cursor.fetchone()
                user_name = user_row[0] if user_row else "用户"
                
                # 2. 获取用户输入和 AI 输出
                cursor.execute("""
                    SELECT 
                        t.interview_original_text_id,
                        t.created_time,
                        t.speaker_type,
                        t.original_text,
                        t.has_voice,
                        v.original_voice_url
                    FROM interview_original_text t
                    LEFT JOIN interview_original_voice v 
                        ON t.interview_original_text_id = v.link_original_text_id
                    WHERE t.user_id = %s 
                        AND t.created_time >= %s 
                        AND t.created_time <= %s
                    ORDER BY t.created_time ASC
                """, (user_id, start_time, end_time))
                
                for row in cursor.fetchall():
                    text_id, created_time, speaker_type, text, has_voice, voice_url = row
                    
                    log_type = "user_input" if speaker_type == 0 else "ai_output"
                    data_type = "user" if speaker_type == 0 else "intv_output"
                    
                    logs.append({
                        "timestamp": created_time.isoformat(),
                        "log_type": log_type,
                        "data_type": data_type,
                        "content": text,
                        "has_audio": has_voice,
                        "audio_url": voice_url,
                        "user_name": user_name if speaker_type == 0 else None,
                        "record_id": f"text_{text_id}"
                    })
                
                # 3. 获取 ASR 调用记录
                cursor.execute("""
                    SELECT 
                        a.processed_id,
                        a.created_time,
                        a.original_text_id,
                        a.duration,
                        a.processed_cost,
                        m.model_name_cn
                    FROM asr_processed a
                    LEFT JOIN base_models m ON a.model_id = m.model_id
                    WHERE a.original_text_id IN (
                        SELECT interview_original_text_id 
                        FROM interview_original_text 
                        WHERE user_id = %s 
                            AND created_time >= %s 
                            AND created_time <= %s
                    )
                    ORDER BY a.created_time ASC
                """, (user_id, start_time, end_time))
                
                for row in cursor.fetchall():
                    processed_id, created_time, text_id, duration, cost, model_name = row
                    
                    logs.append({
                        "timestamp": created_time.isoformat(),
                        "log_type": "asr_call",
                        "model_name": model_name or "未知模型",
                        "duration_ms": duration,
                        "cost": float(cost) if cost else 0,
                        "related_text_id": text_id,
                        "record_id": f"asr_{processed_id}"
                    })
                
                # 4. 获取 TTS 调用记录
                cursor.execute("""
                    SELECT 
                        t.processed_id,
                        t.created_time,
                        t.link_original_text_id,
                        t.duration,
                        t.processed_cost,
                        m.model_name_cn
                    FROM tts_processed t
                    LEFT JOIN base_models m ON t.model_id = m.model_id
                    WHERE t.link_original_text_id IN (
                        SELECT interview_original_text_id 
                        FROM interview_original_text 
                        WHERE user_id = %s 
                            AND created_time >= %s 
                            AND created_time <= %s
                    )
                    ORDER BY t.created_time ASC
                """, (user_id, start_time, end_time))
                
                for row in cursor.fetchall():
                    processed_id, created_time, text_id, duration, cost, model_name = row
                    
                    logs.append({
                        "timestamp": created_time.isoformat(),
                        "log_type": "tts_call",
                        "model_name": model_name or "未知模型",
                        "duration_ms": duration,
                        "cost": float(cost) if cost else 0,
                        "related_text_id": text_id,
                        "record_id": f"tts_{processed_id}"
                    })
                
                # 5. 获取 LLM 调用记录
                cursor.execute("""
                    SELECT 
                        model_processed_id,
                        created_time,
                        agent,
                        model_name_cn,
                        input,
                        output,
                        total_tokens,
                        prompt_tokens,
                        completion_tokens,
                        cached_tokens,
                        process_duration,
                        processed_cost
                    FROM llm_processed
                    WHERE user_id = %s 
                        AND created_time >= %s 
                        AND created_time <= %s
                    ORDER BY created_time ASC
                """, (user_id, start_time, end_time))
                
                for row in cursor.fetchall():
                    (processed_id, created_time, agent, model_name, 
                     llm_input, llm_output, total_tokens, prompt_tokens, 
                     completion_tokens, cached_tokens, duration, cost) = row
                    
                    logs.append({
                        "timestamp": created_time.isoformat(),
                        "log_type": "llm_call",
                        "agent": agent,
                        "model_name": model_name,
                        "llm_input": llm_input,
                        "llm_output": llm_output,
                        "tokens": {
                            "total": total_tokens or 0,
                            "prompt": prompt_tokens or 0,
                            "completion": completion_tokens or 0,
                            "cached": cached_tokens or 0
                        },
                        "duration_ms": duration,
                        "cost": float(cost) if cost else 0,
                        "record_id": f"llm_{processed_id}"
                    })
                
                # 6. 按时间排序
                logs.sort(key=lambda x: x["timestamp"])
                
    except Exception as e:
        logging.error(f"❌ 聚合日志失败: {e}", exc_info=True)
    
    return logs

