#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库日志记录模块
提供 ASR 和 TTS 调用记录到数据库的功能
"""

import logging
from .database import get_db_connection

logging.basicConfig(level=logging.INFO)


def log_asr_call(user_id: str, original_text_id: int, model_id: int, duration_ms: int, cost: float):
    """
    记录 ASR 调用到数据库
    
    Args:
        user_id: 用户ID
        original_text_id: 关联的文本ID (interview_original_text.interview_original_text_id)
        model_id: 模型ID (base_models.model_id)
        duration_ms: 处理耗时(毫秒)
        cost: 成本
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO asr_processed 
                    (original_text_id, model_id, duration, processed_cost)
                    VALUES (%s, %s, %s, %s)
                    RETURNING processed_id
                """, (original_text_id, model_id, duration_ms, cost))
                
                processed_id = cursor.fetchone()[0]
                conn.commit()
                
                logging.info(f"✅ ASR 调用已记录: processed_id={processed_id}, text_id={original_text_id}, duration={duration_ms}ms, cost=¥{cost}")
                return processed_id
    except Exception as e:
        logging.error(f"❌ 记录 ASR 调用失败: {e}", exc_info=True)
        return None


def log_tts_call(user_id: str, link_original_text_id: int, link_original_voice_id: int, 
                 model_id: int, duration_ms: int, cost: float):
    """
    记录 TTS 调用到数据库
    
    Args:
        user_id: 用户ID
        link_original_text_id: 关联的文本ID (interview_original_text.interview_original_text_id)
        link_original_voice_id: 关联的音频ID (interview_original_voice.original_voice_id)
        model_id: 模型ID (base_models.model_id)
        duration_ms: 处理耗时(毫秒)
        cost: 成本
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO tts_processed 
                    (link_original_text_id, link_original_voice_id, model_id, duration, processed_cost)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING processed_id
                """, (link_original_text_id, link_original_voice_id, model_id, duration_ms, cost))
                
                processed_id = cursor.fetchone()[0]
                conn.commit()
                
                logging.info(f"✅ TTS 调用已记录: processed_id={processed_id}, text_id={link_original_text_id}, voice_id={link_original_voice_id}, duration={duration_ms}ms, cost=¥{cost}")
                return processed_id
    except Exception as e:
        logging.error(f"❌ 记录 TTS 调用失败: {e}", exc_info=True)
        return None


def get_model_id_by_name(model_name: str):
    """
    根据模型名称获取模型ID
    
    Args:
        model_name: 模型名称
        
    Returns:
        model_id 或 None
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT model_id FROM base_models 
                    WHERE model_name_cn = %s OR model_name_en = %s
                    LIMIT 1
                """, (model_name, model_name))
                
                row = cursor.fetchone()
                return row[0] if row else None
    except Exception as e:
        logging.error(f"❌ 查询模型ID失败: {e}")
        return None
