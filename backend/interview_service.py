#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
访谈记录服务

管理访谈对话的原文记录和语音文件存储。
"""
from datetime import datetime
from .database import get_db_connection
import logging

logging.basicConfig(level=logging.INFO)


def save_original_text(session_id: str, user_id: str, text: str, speaker_type: int):
    """
    保存对话原文
    
    Args:
        session_id: 会话 ID
        user_id: 用户 ID
        text: 对话文本
        speaker_type: 说话人类型（0=用户, 1=AI）
    
    Returns:
        original_text_id: 新创建的记录 ID
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO interview_original_text 
                    (session_id, user_id, original_text, speaker_type, created_time)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING original_text_id
                """, (session_id, user_id, text, speaker_type, datetime.now()))
                
                original_text_id = cursor.fetchone()[0]
                conn.commit()
        
        speaker_name = "用户" if speaker_type == 0 else "AI"
        logging.info(f"✅ 保存对话原文: {speaker_name}, 字数={len(text)}, id={original_text_id}")
        
        return original_text_id
        
    except Exception as e:
        logging.error(f"❌ 保存对话原文失败: {e}")
        raise


def save_original_voice(user_id: str, speaker_type: int, audio_url: str, link_original_text_id: int = None):
    """
    保存语音文件 URL (带重试机制)
    
    Args:
        user_id: 用户 ID
        speaker_type: 说话人类型（0=用户, 1=AI）
        audio_url: 语音文件 URL
        link_original_text_id: 关联的文本 ID
    
    Returns:
        interview_original_voice_id: 新创建的记录 ID
    """
    import time
    
    max_retries = 3
    retry_delay = 0.5  # 秒
    
    for attempt in range(max_retries):
        try:
            # 🔧 修复: 每次尝试都使用新的数据库连接,避免连接超时问题
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        INSERT INTO interview_original_voice 
                        (user_id, speaker_type, original_voice_url, link_original_text_id)
                        VALUES (%s, %s, %s, %s)
                        RETURNING interview_original_voice_id
                    """, (user_id, speaker_type, audio_url, link_original_text_id))
                    
                    voice_id = cursor.fetchone()[0]
                    conn.commit()
            
            speaker_name = "用户" if speaker_type == 0 else "AI"
            logging.info(f"✅ 保存语音文件: {speaker_name}, url={audio_url[:50]}..., id={voice_id}")
            
            return voice_id
            
        except Exception as e:
            speaker_name = "用户" if speaker_type == 0 else "AI"
            
            if attempt < max_retries - 1:
                # 还有重试机会
                logging.warning(f"⚠️ 保存语音文件失败 (尝试 {attempt + 1}/{max_retries}): {e}, 将在 {retry_delay}s 后重试...")
                time.sleep(retry_delay)
                retry_delay *= 2  # 指数退避
            else:
                # 最后一次尝试也失败了
                logging.error(f"❌ 保存语音文件失败 ({max_retries} 次尝试后): {e}")
                logging.error(f"❌ 丢失的音频 URL: {audio_url}")
                logging.error(f"❌ 关联信息: user_id={user_id}, speaker={speaker_name}, text_id={link_original_text_id}")
                raise


def get_session_history(session_id: str, limit: int = 50):
    """
    获取会话的历史对话记录
    
    Args:
        session_id: 会话 ID
        limit: 最多返回的记录数
    
    Returns:
        对话记录列表
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT original_text_id, original_text, speaker_type, created_time
                    FROM interview_original_text
                    WHERE session_id = %s
                    ORDER BY created_time DESC
                    LIMIT %s
                """, (session_id, limit))
                
                results = cursor.fetchall()
        
        history = []
        for row in results:
            history.append({
                'original_text_id': row[0],
                'original_text': row[1],
                'speaker_type': row[2],
                'created_time': row[3]
            })
        
        # 反转顺序（从旧到新）
        history.reverse()
        
        return history
        
    except Exception as e:
        logging.error(f"❌ 获取会话历史失败: {e}")
        return []


def get_session_word_count(session_id: str) -> int:
    """
    统计会话的总字数
    
    Args:
        session_id: 会话 ID
    
    Returns:
        总字数
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT SUM(LENGTH(original_text))
                    FROM interview_original_text
                    WHERE session_id = %s
                """, (session_id,))
                
                result = cursor.fetchone()
        
        word_count = result[0] if result[0] else 0
        return word_count
        
    except Exception as e:
        logging.error(f"❌ 统计会话字数失败: {e}")
        return 0



def get_latest_ai_message(user_id: str):
    """
    获取用户最新的 AI 回复内容
    
    Args:
        user_id: 用户 ID
    
    Returns:
        最新 AI 回复的文本内容,如果没有则返回 None
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT original_text
                    FROM interview_original_text
                    WHERE user_id = %s AND speaker_type = 1
                    ORDER BY created_time DESC
                    LIMIT 1
                """, (user_id,))
                
                result = cursor.fetchone()
        
        if result:
            logging.info(f"✅ 获取最新 AI 回复: user_id={user_id}, 字数={len(result[0])}")
            return result[0]
        else:
            logging.info(f"📭 未找到 AI 回复记录: user_id={user_id}")
            return None
        
    except Exception as e:
        logging.error(f"❌ 获取最新 AI 回复失败: {e}")
        return None

