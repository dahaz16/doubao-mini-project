#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
Narration Service (讲述状态管理服务)
============================================================================

统一管理 narration_status 表，包括：
- 三个 Agent (Intv/Stn/Dir) 的 Session 生命周期
- 对话缓存池 (chat_cachepool_content) 的读写
- Session 有效性检查 (字数/时间/ID)

根据《服务端流程文档与数据库结构设计 v3.3》设计。
"""

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional, Dict, Any, Tuple
from .database import get_db_connection
from .config_manager import get_config

logging.basicConfig(level=logging.INFO)


# ============================================================================
# 获取/创建用户讲述状态
# ============================================================================

def get_or_create_narration_status(user_id: str) -> Dict[str, Any]:
    """
    获取或创建用户的讲述状态记录
    
    如果用户没有记录则创建一条新记录
    返回完整的 narration_status 字典
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    narration_status_id, user_id,
                    intv_llm_session_id, intv_llm_session_word_count, 
                    intv_llm_session_expire_at, intv_llm_session_previous_response_id,
                    intv_llm_previous_content, intv_llm_hint_id,
                    stn_llm_session_id, stn_llm_session_word_count,
                    stn_llm_session_expire_at, stn_llm_session_previous_response_id,
                    stn_unprocessed_content,
                    dir_llm_session_id, dir_llm_session_word_count,
                    dir_llm_session_expire_at, dir_llm_session_previous_response_id,
                    chat_cachepool_content
                FROM narration_status
                WHERE user_id = %s
            """, (user_id,))
            
            row = cursor.fetchone()
            
            if row:
                return _row_to_dict(row)
            
            # 创建新记录前，先确保用户存在
            cursor.execute("SELECT user_id FROM users WHERE user_id = %s", (user_id,))
            if not cursor.fetchone():
                logging.info(f"⚠️ 用户不存在，创建占位用户: {user_id}")
                # 生成默认 user_name
                default_user_name = f"用户_{user_id[:8]}"
                cursor.execute("""
                    INSERT INTO users (user_id, wechat_openid, wechat_nickname, wechat_avatar_url, user_name)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (user_id) DO NOTHING
                """, (user_id, f'temp_{user_id[:8]}', '临时用户', None, default_user_name))
            
            # 创建新记录
            cursor.execute("""
                INSERT INTO narration_status (user_id)
                VALUES (%s)
                RETURNING narration_status_id
            """, (user_id,))
            conn.commit()
            
            logging.info(f"✅ 创建用户讲述状态: user_id={user_id}")
            
            # 返回新建的记录
            return get_or_create_narration_status(user_id)


def _row_to_dict(row) -> Dict[str, Any]:
    """将数据库行转换为字典"""
    return {
        'narration_status_id': row[0],
        'user_id': str(row[1]),
        'intv_llm_session_id': str(row[2]) if row[2] else None,
        'intv_llm_session_word_count': row[3] or 0,
        'intv_llm_session_expire_at': row[4],
        'intv_llm_session_previous_response_id': row[5],
        'intv_llm_previous_content': row[6],
        'intv_llm_hint_id': row[7],
        'stn_llm_session_id': str(row[8]) if row[8] else None,
        'stn_llm_session_word_count': row[9] or 0,
        'stn_llm_session_expire_at': row[10],
        'stn_llm_session_previous_response_id': row[11],
        'stn_unprocessed_content': row[12],
        'dir_llm_session_id': str(row[13]) if row[13] else None,
        'dir_llm_session_word_count': row[14] or 0,
        'dir_llm_session_expire_at': row[15],
        'dir_llm_session_previous_response_id': row[16],
        'chat_cachepool_content': row[17],
    }


# ============================================================================
# Session 有效性检查 (通用逻辑)
# ============================================================================

def _check_session_valid(
    session_id: Optional[str],
    word_count: int,
    expire_at: Optional[datetime],
    word_limit_key: str,
    expire_buf_key: str
) -> Tuple[bool, str]:
    """
    通用的 Session 有效性检查
    
    返回: (是否有效, 无效原因)
    """
    # 条件1: session_id 为空
    if not session_id:
        return False, "session_id 为空"
    
    # 条件2: 字数超限
    word_limit = int(get_config(word_limit_key, default=20000))
    if word_count > word_limit:
        return False, f"字数超限 ({word_count} > {word_limit})"
    
    # 条件3: 时间即将超限
    if expire_at:
        expire_buf = int(get_config(expire_buf_key, default=300))
        now = datetime.now(timezone.utc)
        
        # 确保 expire_at 有时区信息
        if expire_at.tzinfo is None:
            expire_at = expire_at.replace(tzinfo=timezone.utc)
        
        time_remaining = (expire_at - now).total_seconds()
        if time_remaining < expire_buf:
            return False, f"即将过期 (剩余 {time_remaining:.0f}s < {expire_buf}s)"
    else:
        return False, "expire_at 为空"
    
    return True, "有效"


def check_intv_session_valid(user_id: str) -> Tuple[bool, str]:
    """判断 Intv Session 是否可用"""
    status = get_or_create_narration_status(user_id)
    return _check_session_valid(
        session_id=status['intv_llm_session_id'],
        word_count=status['intv_llm_session_word_count'],
        expire_at=status['intv_llm_session_expire_at'],
        word_limit_key='intv_llm_session_word_limit',
        expire_buf_key='intv_llm_session_expire_buf'
    )


def check_stn_session_valid(user_id: str) -> Tuple[bool, str]:
    """判断 Stn Session 是否可用"""
    status = get_or_create_narration_status(user_id)
    return _check_session_valid(
        session_id=status['stn_llm_session_id'],
        word_count=status['stn_llm_session_word_count'],
        expire_at=status['stn_llm_session_expire_at'],
        word_limit_key='stn_llm_session_word_limit',
        expire_buf_key='stn_llm_session_expire_buf'
    )


def check_dir_session_valid(user_id: str) -> Tuple[bool, str]:
    """判断 Dir Session 是否可用"""
    status = get_or_create_narration_status(user_id)
    return _check_session_valid(
        session_id=status['dir_llm_session_id'],
        word_count=status['dir_llm_session_word_count'],
        expire_at=status['dir_llm_session_expire_at'],
        word_limit_key='dir_llm_session_word_limit',
        expire_buf_key='dir_llm_session_expire_buf'
    )


# ============================================================================
# Session 状态更新
# ============================================================================

def update_intv_session(
    user_id: str,
    session_id: str = None,
    word_count_delta: int = None,
    expire_at: datetime = None,
    previous_response_id: str = None,
    previous_content: str = None,
    hint_id: int = None,
    reset: bool = False
):
    """
    更新 Intv Session 状态
    
    Args:
        reset: 如果为 True，则重置 session 相关字段
    """
    updates = []
    params = []
    
    if reset:
        expire_duration = int(get_config('intv_llm_session_expire_duration', default=3600))
        new_expire_at = datetime.now(timezone.utc) + timedelta(seconds=expire_duration)
        
        updates.extend([
            "intv_llm_session_id = NULL",
            "intv_llm_session_word_count = 0",
            "intv_llm_session_expire_at = %s",
            "intv_llm_session_previous_response_id = NULL"
        ])
        params.append(new_expire_at)
    else:
        if session_id is not None:
            updates.append("intv_llm_session_id = %s")
            params.append(session_id)
        
        if word_count_delta is not None:
            updates.append("intv_llm_session_word_count = intv_llm_session_word_count + %s")
            params.append(word_count_delta)
        
        if expire_at is not None:
            updates.append("intv_llm_session_expire_at = %s")
            params.append(expire_at)
        
        if previous_response_id is not None:
            updates.append("intv_llm_session_previous_response_id = %s")
            params.append(previous_response_id)
    
    if previous_content is not None:
        updates.append("intv_llm_previous_content = %s")
        params.append(previous_content)
    
    if hint_id is not None:
        updates.append("intv_llm_hint_id = %s")
        params.append(hint_id)
    
    if updates:
        params.append(user_id)
        _execute_update(updates, params)


def update_stn_session(
    user_id: str,
    session_id: str = None,
    word_count_delta: int = None,
    expire_at: datetime = None,
    previous_response_id: str = None,
    unprocessed_content: str = None,
    reset: bool = False
):
    """更新 Stn Session 状态"""
    updates = []
    params = []
    
    if reset:
        expire_duration = int(get_config('stn_llm_session_expire_duration', default=3600))
        new_expire_at = datetime.now(timezone.utc) + timedelta(seconds=expire_duration)
        
        updates.extend([
            "stn_llm_session_id = NULL",
            "stn_llm_session_word_count = 0",
            "stn_llm_session_expire_at = %s",
            "stn_llm_session_previous_response_id = NULL"
        ])
        params.append(new_expire_at)
    else:
        if session_id is not None:
            updates.append("stn_llm_session_id = %s")
            params.append(session_id)
        
        if word_count_delta is not None:
            updates.append("stn_llm_session_word_count = stn_llm_session_word_count + %s")
            params.append(word_count_delta)
        
        if expire_at is not None:
            updates.append("stn_llm_session_expire_at = %s")
            params.append(expire_at)
        
        if previous_response_id is not None:
            updates.append("stn_llm_session_previous_response_id = %s")
            params.append(previous_response_id)
    
    if unprocessed_content is not None:
        updates.append("stn_unprocessed_content = %s")
        params.append(unprocessed_content)
    
    if updates:
        params.append(user_id)
        _execute_update(updates, params)


def update_dir_session(
    user_id: str,
    session_id: str = None,
    word_count_delta: int = None,
    expire_at: datetime = None,
    previous_response_id: str = None,
    reset: bool = False
):
    """更新 Dir Session 状态"""
    updates = []
    params = []
    
    if reset:
        expire_duration = int(get_config('dir_llm_session_expire_duration', default=3600))
        new_expire_at = datetime.now(timezone.utc) + timedelta(seconds=expire_duration)
        
        updates.extend([
            "dir_llm_session_id = NULL",
            "dir_llm_session_word_count = 0",
            "dir_llm_session_expire_at = %s",
            "dir_llm_session_previous_response_id = NULL"
        ])
        params.append(new_expire_at)
    else:
        if session_id is not None:
            updates.append("dir_llm_session_id = %s")
            params.append(session_id)
        
        if word_count_delta is not None:
            updates.append("dir_llm_session_word_count = dir_llm_session_word_count + %s")
            params.append(word_count_delta)
        
        if expire_at is not None:
            updates.append("dir_llm_session_expire_at = %s")
            params.append(expire_at)
        
        if previous_response_id is not None:
            updates.append("dir_llm_session_previous_response_id = %s")
            params.append(previous_response_id)
    
    if updates:
        params.append(user_id)
        _execute_update(updates, params)


def _execute_update(updates: list, params: list):
    """执行更新语句"""
    sql = f"UPDATE narration_status SET {', '.join(updates)} WHERE user_id = %s"
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(sql, params)
            conn.commit()


# ============================================================================
# 对话缓存池操作
# ============================================================================

def append_cachepool(user_id: str, speaker: str, text: str) -> int:
    """
    追加内容到缓存池
    
    Args:
        speaker: "U" (用户) 或 "I" (AI)
        text: 原始文本
    
    Returns:
        更新后的缓存池总字数
    """
    formatted = f"{speaker}:{text} "
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE narration_status 
                SET chat_cachepool_content = COALESCE(chat_cachepool_content, '') || %s
                WHERE user_id = %s
                RETURNING LENGTH(chat_cachepool_content)
            """, (formatted, user_id))
            
            result = cursor.fetchone()
            conn.commit()
            
            total_len = result[0] if result else 0
            logging.info(f"📝 缓存池追加: {speaker}:{text[:20]}... (总字数: {total_len})")
            return total_len


def take_cachepool_snapshot(user_id: str) -> Optional[str]:
    """
    快照并清空缓存池（原子操作）
    
    PRD 5.2.2 执行逻辑：
    1. 快照提取：将当前 chat_cachepool_content 赋值给临时变量
    2. 立即清空：原子性操作清空数据库中的 chat_cachepool_content
    
    Returns:
        缓存池快照内容，如果为空返回 None
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                UPDATE narration_status
                SET chat_cachepool_content = NULL
                WHERE user_id = %s
                RETURNING chat_cachepool_content
            """, (user_id,))
            
            # 注意：这里返回的是更新前的值（PostgreSQL 特性）
            # 需要改用不同的方式
            conn.rollback()
            
            # 使用两步操作但确保原子性
            cursor.execute("""
                SELECT chat_cachepool_content FROM narration_status
                WHERE user_id = %s FOR UPDATE
            """, (user_id,))
            result = cursor.fetchone()
            
            content = result[0] if result and result[0] else None
            
            if content:
                cursor.execute("""
                    UPDATE narration_status
                    SET chat_cachepool_content = NULL
                    WHERE user_id = %s
                """, (user_id,))
                conn.commit()
                
                logging.info(f"📸 缓存池快照: {len(content)} 字符")
            
            return content


def check_cachepool_threshold(user_id: str) -> Tuple[bool, int]:
    """
    检测缓存池是否达到触发阈值
    
    Returns:
        (是否触发, 当前字数)
    """
    status = get_or_create_narration_status(user_id)
    content = status.get('chat_cachepool_content') or ''
    current_len = len(content)
    
    threshold = int(get_config('cache_pool_limit', default=200))
    should_trigger = current_len >= threshold
    
    if should_trigger:
        logging.info(f"🔔 缓存池触发: {current_len} >= {threshold}")
    
    return should_trigger, current_len


# ============================================================================
# 前情提要获取 (Intv Agent 新建 Session 时使用)
# ============================================================================

def get_intv_previous_content(user_id: str, limit: int = 9) -> str:
    """
    获取最新的对话记录作为前情提要
    
    PRD 5.1.3：按 created_time 倒序取最新 9 条对话（跳过当前刚存入的那 1 条），恢复时间正序
    格式：speaker_type == 1 拼接 "I:", speaker_type == 0 拼接 "U:"
    
    Updated: 增加 OFFSET 1，确保 pc 不包含本轮的 current_input
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT speaker_type, original_text
                FROM interview_original_text
                WHERE user_id = %s
                ORDER BY created_time DESC
                LIMIT %s OFFSET 1
            """, (user_id, limit))
            
            rows = cursor.fetchall()
            
            if not rows:
                return ""
            
            # 倒序取出后需要恢复正序
            rows = list(reversed(rows))
            
            parts = []
            for speaker_type, text in rows:
                prefix = "I:" if speaker_type == 1 else "U:"
                parts.append(f"{prefix}{text}")
            
            return " ".join(parts)


# ============================================================================
# Hintboard 相关
# ============================================================================

def get_latest_hint(user_id: str) -> Tuple[Optional[int], Optional[str]]:
    """
    获取用户最新的 hint
    
    Returns:
        (hint_id, hint_content)
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT hint_id, hint_content
                FROM hintboard
                WHERE user_id = %s
                ORDER BY created_time DESC
                LIMIT 1
            """, (user_id,))
            
            row = cursor.fetchone()
            
            if row:
                return row[0], row[1]
            return None, None


def check_hint_updated(user_id: str) -> Tuple[bool, Optional[int], Optional[str]]:
    """
    检查 hintboard 是否有更新
    
    PRD 5.1.4: 判断 hintboard 最新 hint_id 是否等于 narration_status 中的 intv_llm_hint_id
    
    Returns:
        (是否更新, 新 hint_id, 新 hint_content)
    """
    status = get_or_create_narration_status(user_id)
    current_hint_id = status.get('intv_llm_hint_id')
    
    latest_hint_id, latest_hint_content = get_latest_hint(user_id)
    
    if latest_hint_id is None:
        return False, None, None
    
    if current_hint_id != latest_hint_id:
        return True, latest_hint_id, latest_hint_content
    
    return False, None, None


def insert_hint(user_id: str, hint_content: str) -> int:
    """
    插入新的 hint
    
    Returns:
        新插入的 hint_id
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                INSERT INTO hintboard (user_id, hint_content)
                VALUES (%s, %s)
                RETURNING hint_id
            """, (user_id, hint_content))
            
            hint_id = cursor.fetchone()[0]
            conn.commit()
            
            logging.info(f"💡 插入 Hint: hint_id={hint_id}")
            return hint_id
