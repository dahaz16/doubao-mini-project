#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对话缓存池服务模块

处理对话内容的缓存、字数统计和阈值触发，并对接 Stn Agent（速记员）
"""
import logging
from .database import get_db_connection
from .config_manager import get_config
from datetime import datetime
from .stn_service import run_stn_agent_async

logging.basicConfig(level=logging.INFO)

def add_to_cachepool(session_id: str, user_id: str, speaker_type: int, text: str) -> dict:
    """
    添加对话内容到缓存池
    
    Args:
        session_id: 会话ID
        user_id: 用户ID
        speaker_type: 0=用户, 1=AI
        text: 对话文本
    
    Returns:
        {
            'current_word_count': int,
            'threshold_reached': bool,
            'cache_content': str,
            'cachepool_id': int
        }
    """
    try:
        # 获取阈值配置
        threshold = int(get_config('cache_pool_limit'))
        
        # 格式化新内容
        prefix = "U: " if speaker_type == 0 else "I: "
        new_content = f"{prefix}{text.strip()}"
        
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # 查询当前 session 未处理的缓存池内容 (stn_processed_type = 0)
                cursor.execute("""
                    SELECT cache_content, word_count, cachepool_id
                    FROM chat_cachepool
                    WHERE session_id = %s AND is_processed = FALSE
                    ORDER BY created_time DESC
                    LIMIT 1
                """, (session_id,))
                
                existing = cursor.fetchone()
                
                if existing:
                    # 有记录，追加
                    old_content, _, pool_id = existing
                    combined_content = f"{old_content}\n{new_content}"
                    new_count = len(combined_content)
                    
                    cursor.execute("""
                        UPDATE chat_cachepool
                        SET cache_content = %s, word_count = %s
                        WHERE cachepool_id = %s
                    """, (combined_content, new_count, pool_id))
                    conn.commit()
                    logging.info(f"📝 缓存池更新 (ID: {pool_id}): {new_count} 字")
                else:
                    # 新建
                    combined_content = new_content
                    new_count = len(combined_content)
                    
                    cursor.execute("""
                        INSERT INTO chat_cachepool
                        (user_id, session_id, cache_content, word_count, is_processed, created_time)
                        VALUES (%s, %s, %s, %s, FALSE, %s)
                        RETURNING cachepool_id
                    """, (user_id, session_id, combined_content, new_count, datetime.now()))
                    
                    pool_id = cursor.fetchone()[0]
                    conn.commit()
                    logging.info(f"📝 缓存池新建 (ID: {pool_id}): {new_count} 字")
                
                # 检查阈值
                threshold_reached = new_count >= threshold
                
                if threshold_reached:
                    logging.info(f"🔔 缓存池已满 ({new_count}/{threshold})，触发 Stn Agent...")
                    
                    # 异步触发速记员 (stn_service 会负责把状态改为 1 处理中)
                    run_stn_agent_async(user_id, session_id, combined_content, pool_id)

                    return {
                        'current_word_count': new_count,
                        'threshold_reached': True,
                        'cache_content': combined_content,
                        'cachepool_id': pool_id
                    }
                
                return {
                    'current_word_count': new_count,
                    'threshold_reached': False,
                    'cache_content': combined_content,
                    'cachepool_id': pool_id
                }
                    
    except Exception as e:
        logging.error(f"❌ 缓存池添加失败: {e}", exc_info=True)
        return {'current_word_count': 0, 'threshold_reached': False, 'cache_content': '', 'cachepool_id': None}

def get_cachepool_content(session_id: str) -> str:
    """获取 session 当前缓存内容"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT cache_content
                    FROM chat_cachepool
                    WHERE session_id = %s AND is_processed = FALSE
                    ORDER BY created_time DESC LIMIT 1
                """, (session_id,))
                result = cursor.fetchone()
                return result[0] if result else ""
    except Exception as e:
        logging.error(f"❌ 获取缓存内容失败: {e}")
        return ""
