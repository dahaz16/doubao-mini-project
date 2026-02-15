
# -*- coding: utf-8 -*-
import logging
from typing import List, Optional, Dict, Any
from .database import get_db_connection
from datetime import datetime

def submit_feedback(user_id: str, content: str, voice_url: Optional[str] = None) -> int:
    """
    提交用户反馈
    
    Args:
        user_id: 用户 ID
        content: 反馈内容
        voice_url: 语音文件 URL (可选)
        
    Returns:
        feedback_id: 新增反馈的 ID
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO feedback (user_id, feedback_content, feedback_voice_url)
                    VALUES (%s, %s, %s)
                    RETURNING feedback_id
                """, (user_id, content, voice_url))
                
                feedback_id = cursor.fetchone()[0]
                conn.commit()
                logging.info(f"✅ 用户 {user_id} 提交反馈成功, ID: {feedback_id}")
                return feedback_id
                
    except Exception as e:
        logging.error(f"❌ 提交反馈失败: {e}")
        raise

def get_feedback_list(user_id: str) -> List[Dict[str, Any]]:
    """
    获取用户的反馈列表
    
    Args:
        user_id: 用户 ID
        
    Returns:
        feedback_list: 反馈记录列表
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT feedback_id, user_id, feedback_content, feedback_voice_url, created_time
                    FROM feedback
                    WHERE user_id = %s
                    ORDER BY created_time ASC
                """, (user_id,))
                
                columns = [desc[0] for desc in cursor.description]
                rows = cursor.fetchall()
                
                result = []
                for row in rows:
                    item = dict(zip(columns, row))
                    # 确保时间格式一致
                    if item['created_time']:
                        item['created_time'] = item['created_time'].isoformat()
                    result.append(item)
                    
                return result
                
    except Exception as e:
        logging.error(f"❌ 获取反馈列表失败: {e}")
        raise
