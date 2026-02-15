# -*- coding: utf-8 -*-
"""
============================================================================
Writing Cachepool Service (写作缓存池服务)
============================================================================

负责管理写作素材缓存池的更新逻辑：
1. 将 topic_id 插入 writing_source_cachepool
2. 计算缓存池总字数
3. 更新 writing_status 表

基于《我的故事页需求文档 v0.5.md》实现
"""

import logging
from typing import Optional
from .database import get_db_connection

# Use logging directly for consistency with other services
# logger = logging.getLogger(__name__)


def update_writing_cachepool(user_id: str, topic_id: int) -> bool:
    """
    写作缓存池更新逻辑
    
    当 Topic 新增或更新时调用，执行以下操作：
    1. 检查 topic_id 是否已在 cachepool 中，无则插入
    2. 查询 cachepool 中所有 topic → 读取 topic_title / topic_content
    3. 计算总字数 → 更新 writing_status.cachepool_words_count
    
    Args:
        user_id: 用户 ID
        topic_id: Topic ID
        
    Returns:
        bool: 更新是否成功
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # Step 1: 检查并插入 topic_id 到缓存池
                cursor.execute("""
                    INSERT INTO writing_source_cachepool (topic_id, user_id, created_time)
                    VALUES (%s, %s, CURRENT_TIMESTAMP)
                    ON CONFLICT (topic_id) DO NOTHING
                """, (topic_id, user_id))
                
                # Step 2: 查询该用户缓存池中所有 topic 的内容
                cursor.execute("""
                    SELECT t.topic_title, t.topic_content
                    FROM writing_source_cachepool wsc
                    JOIN topic t ON wsc.topic_id = t.topic_id
                    WHERE wsc.user_id = %s
                    ORDER BY wsc.created_time ASC
                """, (user_id,))
                
                topics = cursor.fetchall()
                
                # Step 3: 计算总字数
                total_words = 0
                for title, content in topics:
                    if title:
                        total_words += len(title)
                    if content:
                        total_words += len(content)
                
                # Step 4: 更新 writing_status
                cursor.execute("""
                    INSERT INTO writing_status (user_id, cachepool_words_count, writing_state, updated_time)
                    VALUES (%s, %s, 0, CURRENT_TIMESTAMP)
                    ON CONFLICT (user_id) 
                    DO UPDATE SET 
                        cachepool_words_count = EXCLUDED.cachepool_words_count,
                        updated_time = CURRENT_TIMESTAMP
                """, (user_id, total_words))
                
                conn.commit()
                
                logging.info(f"✓ Writing cachepool updated for user {user_id}: "
                           f"topic_id={topic_id}, total_words={total_words}")
                return True
                
    except Exception as e:
        logging.error(f"✗ Failed to update writing cachepool for user {user_id}: {e}")
        return False


def get_writing_status(user_id: str) -> Optional[dict]:
    """
    获取用户的写作状态
    
    Args:
        user_id: 用户 ID
        
    Returns:
        dict: {
            'cachepool_words_count': int,
            'writing_state': int,  # 0=pending, 1=writing
            'updated_time': datetime
        }
        None: 用户无写作状态记录
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT cachepool_words_count, writing_state, updated_time
                    FROM writing_status
                    WHERE user_id = %s
                """, (user_id,))
                
                result = cursor.fetchone()
                if not result:
                    return None
                
                return {
                    'cachepool_words_count': result[0],
                    'writing_state': result[1],
                    'updated_time': result[2]
                }
                
    except Exception as e:
        logging.error(f"✗ Failed to get writing status for user {user_id}: {e}")
        return None


def get_pending_topics(user_id: str) -> list:
    """
    获取缓存池中所有待写作的 topic
    
    Args:
        user_id: 用户 ID
        
    Returns:
        list: [{
            'topic_id': int,
            'topic_title': str,
            'topic_content': str,
            'parent_stage_id': int
        }]
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT t.topic_id, t.topic_title, t.topic_content, t.parent_stage_id
                    FROM writing_source_cachepool wsc
                    JOIN topic t ON wsc.topic_id = t.topic_id
                    WHERE wsc.user_id = %s
                    ORDER BY t.topic_id ASC
                """, (user_id,))
                
                topics = []
                for row in cursor.fetchall():
                    topics.append({
                        'topic_id': row[0],
                        'topic_title': row[1],
                        'topic_content': row[2],
                        'parent_stage_id': row[3]
                    })
                
                return topics
                
    except Exception as e:
        logging.error(f"✗ Failed to get pending topics for user {user_id}: {e}")
        return []


def clear_cachepool(user_id: str, topic_ids: list) -> bool:
    """
    清理缓存池中指定的 topic_id
    
    Args:
        user_id: 用户 ID
        topic_ids: 要清理的 topic_id 列表
        
    Returns:
        bool: 清理是否成功
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    DELETE FROM writing_source_cachepool
                    WHERE user_id = %s AND topic_id = ANY(%s)
                """, (user_id, topic_ids))
                
                deleted_count = cursor.rowcount
                
                # 重新计算剩余字数
                cursor.execute("""
                    SELECT t.topic_title, t.topic_content
                    FROM writing_source_cachepool wsc
                    JOIN topic t ON wsc.topic_id = t.topic_id
                    WHERE wsc.user_id = %s
                """, (user_id,))
                
                remaining_topics = cursor.fetchall()
                total_words = sum(
                    len(title or '') + len(content or '')
                    for title, content in remaining_topics
                )
                
                # 更新 writing_status
                cursor.execute("""
                    UPDATE writing_status
                    SET cachepool_words_count = %s,
                        updated_time = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                """, (total_words, user_id))
                
                conn.commit()
                
                logging.info(f"✓ Cleared {deleted_count} topics from cachepool for user {user_id}, "
                           f"remaining words: {total_words}")
                return True
                
    except Exception as e:
        logging.error(f"✗ Failed to clear cachepool for user {user_id}: {e}")
        return False
