#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Session 管理服务

管理访谈会话的生命周期，包括创建、验证、更新和过期管理。
"""
import uuid
from datetime import datetime, timedelta
from .database import get_db_connection
from .config_manager import get_config
import logging

logging.basicConfig(level=logging.INFO)


def create_session(user_id: str) -> str:
    """
    创建新的访谈会话
    
    Args:
        user_id: 用户 ID
    
    Returns:
        session_id: 新创建的会话 ID
    """
    try:
        # 生成会话 ID
        session_id = str(uuid.uuid4())
        
        # 获取配置
        session_ttl = get_config('session_ttl', default=3600)
        
        # 计算过期时间
        expire_at = datetime.now() + timedelta(seconds=session_ttl)
        
        # 插入会话记录
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO interview_sessions 
                    (session_id, user_id, session_start_time, session_expire_at, session_word_count, previous_response_id)
                    VALUES (%s, %s, %s, %s, %s, %s)
                """, (session_id, user_id, datetime.now(), expire_at, 0, None))
                conn.commit()
        
        logging.info(f"✅ 创建会话成功: session_id={session_id}, user_id={user_id}")
        return session_id
        
    except Exception as e:
        logging.error(f"❌ 创建会话失败: {e}")
        raise


def get_session(session_id: str) -> dict:
    """
    获取会话信息
    
    Args:
        session_id: 会话 ID
    
    Returns:
        会话信息字典，如果不存在返回 None
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT session_id, user_id, session_start_time, session_expire_at, 
                           session_word_count, previous_response_id, created_time
                    FROM interview_sessions
                    WHERE session_id = %s
                """, (session_id,))
                
                result = cursor.fetchone()
        
        if result:
            return {
                'session_id': result[0],
                'user_id': result[1],
                'session_start_time': result[2],
                'session_expire_at': result[3],
                'session_word_count': result[4],
                'previous_response_id': result[5],
                'created_time': result[6]
            }
        return None
        
    except Exception as e:
        logging.error(f"❌ 获取会话失败: {e}")
        return None


def validate_session(session_id: str) -> bool:
    """
    验证会话是否有效（未过期）
    
    Args:
        session_id: 会话 ID
    
    Returns:
        True 如果会话有效，False 如果会话不存在或已过期
    """
    session = get_session(session_id)
    
    if not session:
        logging.warning(f"⚠️ 会话不存在: {session_id}")
        return False
    
    # 检查是否过期
    expire_at = session['session_expire_at']
    # 移除时区信息进行比较
    if expire_at.tzinfo:
        expire_at = expire_at.replace(tzinfo=None)
    
    if expire_at < datetime.now():
        logging.warning(f"⚠️ 会话已过期: {session_id}")
        return False
    
    return True


def get_session_response_id(session_id: str) -> str:
    """
    获取会话的 previous_response_id
    
    Args:
        session_id: 会话 ID
    
    Returns:
        previous_response_id，如果不存在返回 None
    """
    session = get_session(session_id)
    
    if session:
        return session['previous_response_id']
    return None


def update_session_response_id(session_id: str, response_id: str):
    """
    更新会话的 previous_response_id
    
    Args:
        session_id: 会话 ID
        response_id: 新的 response_id
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE interview_sessions
                    SET previous_response_id = %s
                    WHERE session_id = %s
                """, (response_id, session_id))
                conn.commit()
        
        logging.info(f"✅ 更新会话 response_id: session_id={session_id}, response_id={response_id[:50]}...")
        
    except Exception as e:
        logging.error(f"❌ 更新会话 response_id 失败: {e}")
        raise


def update_session_word_count(session_id: str, word_count: int):
    """
    更新会话的字数统计
    
    Args:
        session_id: 会话 ID
        word_count: 新增字数
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE interview_sessions
                    SET session_word_count = session_word_count + %s
                    WHERE session_id = %s
                """, (word_count, session_id))
                conn.commit()
        
        logging.info(f"✅ 更新会话字数: session_id={session_id}, 新增={word_count}")
        
    except Exception as e:
        logging.error(f"❌ 更新会话字数失败: {e}")
        raise


def extend_session(session_id: str):
    """
    延长会话过期时间
    
    Args:
        session_id: 会话 ID
    """
    try:
        # 获取配置
        session_ttl = get_config('session_ttl', default=3600)
        
        # 计算新的过期时间
        new_expire_at = datetime.now() + timedelta(seconds=session_ttl)
        
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE interview_sessions
                    SET session_expire_at = %s
                    WHERE session_id = %s
                """, (new_expire_at, session_id))
                conn.commit()
        
        logging.info(f"✅ 延长会话过期时间: session_id={session_id}")
        
    except Exception as e:
        logging.error(f"❌ 延长会话过期时间失败: {e}")
        raise
