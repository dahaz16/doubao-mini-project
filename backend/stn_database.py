#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
Stn Database Module (速记员数据库操作模块) v3.3
============================================================================

负责将 Stn Agent 解析出的结构化回忆数据存入数据库。
适配 v3.3 PRD 表结构，使用新的 storyboard 表字段。
"""

import logging
from typing import Optional, List, Dict, Any, Tuple
from .database import get_db_connection
from .config_manager import get_config

logging.basicConfig(level=logging.INFO)


# ============================================================================
# Stage 操作
# ============================================================================

def insert_stage(
    user_id: str,
    title: str,
    summary: Optional[str] = None,
    content: Optional[str] = None,
    start_time: Optional[str] = None,
    end_time: Optional[str] = None
) -> Optional[int]:
    """插入舞台记录"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO stage (user_id, stage_title, stage_summary, stage_content, stage_start_time, stage_end_time)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING stage_id
                """, (user_id, title, summary, content, start_time, end_time))
                stage_id = cursor.fetchone()[0]
                conn.commit()
                logging.info(f"✅ Stage 插入成功: {stage_id}")
                return stage_id
    except Exception as e:
        logging.error(f"❌ Stage 插入失败: {e}")
        return None


def update_stage(
    stage_id: int,
    title: Optional[str] = None,
    summary: Optional[str] = None,
    content: Optional[str] = None
) -> bool:
    """更新舞台记录"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE stage 
                    SET stage_title = COALESCE(%s, stage_title),
                        stage_summary = COALESCE(%s, stage_summary),
                        stage_content = COALESCE(%s, stage_content)
                    WHERE stage_id = %s
                """, (title, summary, content, stage_id))
                conn.commit()
                logging.info(f"✅ Stage 更新成功: {stage_id}")
                return True
    except Exception as e:
        logging.error(f"❌ Stage 更新失败: {e}")
        return False


# ============================================================================
# Topic 操作
# ============================================================================

def insert_topic(
    user_id: str,
    parent_stage_id: int,
    title: str,
    summary: Optional[str] = None,
    content: Optional[str] = None
) -> Optional[int]:
    """插入话题记录"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO topic (user_id, parent_stage_id, topic_title, topic_summary, topic_content)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING topic_id
                """, (user_id, parent_stage_id, title, summary, content))
                topic_id = cursor.fetchone()[0]
                conn.commit()
                logging.info(f"✅ Topic 插入成功: {topic_id} (Stage: {parent_stage_id})")
                return topic_id
    except Exception as e:
        logging.error(f"❌ Topic 插入失败: {e}")
        return None


def update_topic(
    topic_id: int,
    title: Optional[str] = None,
    summary: Optional[str] = None,
    content: Optional[str] = None,
    parent_stage_id: Optional[int] = None
) -> bool:
    """更新话题记录"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE topic 
                    SET topic_title = COALESCE(%s, topic_title),
                        topic_summary = COALESCE(%s, topic_summary),
                        topic_content = COALESCE(%s, topic_content),
                        parent_stage_id = COALESCE(%s, parent_stage_id)
                    WHERE topic_id = %s
                """, (title, summary, content, parent_stage_id, topic_id))
                conn.commit()
                logging.info(f"✅ Topic 更新成功: {topic_id}")
                return True
    except Exception as e:
        logging.error(f"❌ Topic 更新失败: {e}")
        return False


# ============================================================================
# Shot 操作
# ============================================================================

def insert_shot(
    user_id: str,
    parent_topic_id: int,
    title: str,
    summary: Optional[str] = None,
    content: Optional[str] = None,
    shot_type: int = 1
) -> Optional[int]:
    """插入镜头记录"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO shot (user_id, parent_topic_id, shot_title, shot_summary, shot_content, shot_type)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    RETURNING shot_id
                """, (user_id, parent_topic_id, title, summary, content, shot_type))
                shot_id = cursor.fetchone()[0]
                conn.commit()
                logging.info(f"✅ Shot 插入成功: {shot_id} (Topic: {parent_topic_id})")
                return shot_id
    except Exception as e:
        logging.error(f"❌ Shot 插入失败: {e}")
        return None


def update_shot(
    shot_id: int,
    title: Optional[str] = None,
    summary: Optional[str] = None,
    content: Optional[str] = None,
    shot_type: Optional[int] = None,
    parent_topic_id: Optional[int] = None
) -> bool:
    """更新镜头记录"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE shot 
                    SET shot_title = COALESCE(%s, shot_title),
                        shot_summary = COALESCE(%s, shot_summary),
                        shot_content = COALESCE(%s, shot_content),
                        shot_type = COALESCE(%s, shot_type),
                        parent_topic_id = COALESCE(%s, parent_topic_id)
                    WHERE shot_id = %s
                """, (title, summary, content, shot_type, parent_topic_id, shot_id))
                conn.commit()
                logging.info(f"✅ Shot 更新成功: {shot_id}")
                return True
    except Exception as e:
        logging.error(f"❌ Shot 更新失败: {e}")
        return False


# ============================================================================
# Character 操作
# ============================================================================

def insert_character(
    user_id: str,
    related_shot_id: int,
    name: str,
    relation: Optional[str] = None,
    evaluation: Optional[str] = None
) -> Optional[int]:
    """插入人物记录"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO character (user_id, related_shot_id, name, relation, evaluation)
                    VALUES (%s, %s, %s, %s, %s)
                    RETURNING character_id
                """, (user_id, related_shot_id, name, relation, evaluation))
                char_id = cursor.fetchone()[0]
                conn.commit()
                logging.info(f"✅ Character 插入成功: {char_id} (Shot: {related_shot_id})")
                return char_id
    except Exception as e:
        logging.error(f"❌ Character 插入失败: {e}")
        return None


def update_character(
    character_id: int,
    name: Optional[str] = None,
    relation: Optional[str] = None,
    evaluation: Optional[str] = None,
    related_shot_id: Optional[int] = None
) -> bool:
    """更新人物记录"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE character 
                    SET name = COALESCE(%s, name),
                        relation = COALESCE(%s, relation),
                        evaluation = COALESCE(%s, evaluation),
                        related_shot_id = COALESCE(%s, related_shot_id)
                    WHERE character_id = %s
                """, (name, relation, evaluation, related_shot_id, character_id))
                conn.commit()
                logging.info(f"✅ Character 更新成功: {character_id}")
                return True
    except Exception as e:
        logging.error(f"❌ Character 更新失败: {e}")
        return False


# ============================================================================
# Storyboard 操作 (v3.3 新表结构)
# ============================================================================

def insert_storyboard(
    user_id: str,
    story_type: int,
    entity_id: int,
    story_content: str
) -> Optional[int]:
    """
    插入故事板记录
    
    story_type: 1=Stage, 2=Topic, 3=Shot, 4=Character
    stn_processed_status 默认为 0（新记录，待 Stn 下次使用）
    dir_processed_status 默认为 0（待 Dir 处理）
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO storyboard (user_id, story_type, entity_id, story_content)
                    VALUES (%s, %s, %s, %s)
                    RETURNING story_id
                """, (user_id, story_type, entity_id, story_content))
                story_id = cursor.fetchone()[0]
                conn.commit()
                logging.info(f"✅ Storyboard 插入: story_id={story_id}, type={story_type}, entity={entity_id}")
                return story_id
    except Exception as e:
        logging.error(f"❌ Storyboard 插入失败: {e}")
        return None


def get_unprocessed_storyboards_for_stn(user_id: str) -> List[Dict[str, Any]]:
    """
    获取 stn_processed_status=0 的故事板记录（用于 Stn Session 有效时）
    
    PRD 5.2.3: Stn Session 有效时，获取上次调用后新产生的 SB 记录
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT story_id, story_type, entity_id, story_content
                    FROM storyboard
                    WHERE user_id = %s AND stn_processed_status = 0
                    ORDER BY story_id ASC
                """, (user_id,))
                rows = cursor.fetchall()
                
                return [
                    {
                        'story_id': row[0],
                        'story_type': row[1],
                        'entity_id': row[2],
                        'story_content': row[3]
                    }
                    for row in rows
                ]
    except Exception as e:
        logging.error(f"❌ 获取未处理 SB 失败: {e}")
        return []


def get_latest_storyboards(user_id: str, limit: int = None) -> List[Dict[str, Any]]:
    """
    获取最新的 N 条故事板记录（用于 Stn Session 无效时）
    
    PRD 5.2.3: Stn Session 无效时，获取最新 N 条作为完整上下文
    """
    if limit is None:
        limit = int(get_config('max_sb_context', default=50))
    
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT story_id, story_type, entity_id, story_content
                    FROM storyboard
                    WHERE user_id = %s
                    ORDER BY story_id DESC
                    LIMIT %s
                """, (user_id, limit))
                rows = cursor.fetchall()
                
                # 反转为正序
                return [
                    {
                        'story_id': row[0],
                        'story_type': row[1],
                        'entity_id': row[2],
                        'story_content': row[3]
                    }
                    for row in reversed(rows)
                ]
    except Exception as e:
        logging.error(f"❌ 获取最新 SB 失败: {e}")
        return []


def mark_storyboards_stn_processed(user_id: str, max_story_id: int) -> bool:
    """
    标记故事板记录为 Stn 已处理
    
    将 story_id <= max_story_id 且 stn_processed_status=0 的记录更新为 1
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE storyboard
                    SET stn_processed_status = 1
                    WHERE user_id = %s 
                      AND story_id <= %s 
                      AND stn_processed_status = 0
                """, (user_id, max_story_id))
                affected = cursor.rowcount
                conn.commit()
                logging.info(f"✅ 标记 Stn 已处理: {affected} 条记录")
                return True
    except Exception as e:
        logging.error(f"❌ 标记 Stn 处理状态失败: {e}")
        return False


def get_unprocessed_storyboards_for_dir(user_id: str) -> Tuple[List[Dict[str, Any]], Optional[int]]:
    """
    获取 dir_processed_status=0 的故事板记录（用于 Dir Session 有效时）
    
    PRD 5.3.3: 获取未被 Dir 处理的 SB，并记录 max_dir_read_id
    
    Returns:
        (记录列表, max_story_id)
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT story_id, story_type, entity_id, story_content
                    FROM storyboard
                    WHERE user_id = %s AND dir_processed_status = 0
                    ORDER BY story_id ASC
                """, (user_id,))
                rows = cursor.fetchall()
                
                if not rows:
                    return [], None
                
                max_id = max(row[0] for row in rows)
                
                records = [
                    {
                        'story_id': row[0],
                        'story_type': row[1],
                        'entity_id': row[2],
                        'story_content': row[3]
                    }
                    for row in rows
                ]
                
                return records, max_id
    except Exception as e:
        logging.error(f"❌ 获取 Dir 未处理 SB 失败: {e}")
        return [], None


def mark_storyboards_dir_processed(user_id: str, max_story_id: int) -> bool:
    """
    标记故事板记录为 Dir 已处理
    
    将 story_id <= max_story_id 且 dir_processed_status=0 的记录更新为 1
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE storyboard
                    SET dir_processed_status = 1
                    WHERE user_id = %s 
                      AND story_id <= %s 
                      AND dir_processed_status = 0
                """, (user_id, max_story_id))
                affected = cursor.rowcount
                conn.commit()
                logging.info(f"✅ 标记 Dir 已处理: {affected} 条记录")
                return True
    except Exception as e:
        logging.error(f"❌ 标记 Dir 处理状态失败: {e}")
        return False


def format_storyboards_for_llm(storyboards: List[Dict[str, Any]]) -> str:
    """将故事板记录格式化为 LLM 输入字符串"""
    if not storyboards:
        return ""
    return "\n".join([sb['story_content'] for sb in storyboards])


# ============================================================================
# 实体查询（用于 Update 操作时查找现有 ID）
# ============================================================================

def find_stage_by_title(user_id: str, title: str) -> Optional[int]:
    """通过标题查找舞台 ID"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT stage_id FROM stage
                    WHERE user_id = %s AND stage_title = %s
                    ORDER BY created_time DESC
                    LIMIT 1
                """, (user_id, title))
                row = cursor.fetchone()
                return row[0] if row else None
    except Exception as e:
        logging.error(f"❌ 查找 Stage 失败: {e}")
        return None


def find_topic_by_title(user_id: str, title: str) -> Optional[int]:
    """通过标题查找话题 ID"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT topic_id FROM topic
                    WHERE user_id = %s AND topic_title = %s
                    ORDER BY created_time DESC
                    LIMIT 1
                """, (user_id, title))
                row = cursor.fetchone()
                return row[0] if row else None
    except Exception as e:
        logging.error(f"❌ 查找 Topic 失败: {e}")
        return None


def find_shot_by_title(user_id: str, title: str) -> Optional[int]:
    """通过标题查找镜头 ID"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT shot_id FROM shot
                    WHERE user_id = %s AND shot_title = %s
                    ORDER BY created_time DESC
                    LIMIT 1
                """, (user_id, title))
                row = cursor.fetchone()
                return row[0] if row else None
    except Exception as e:
        logging.error(f"❌ 查找 Shot 失败: {e}")
        return None


def find_character_by_name(user_id: str, name: str) -> Optional[int]:
    """通过名字查找人物 ID"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT character_id FROM character
                    WHERE user_id = %s AND name = %s
                    ORDER BY created_time DESC
                    LIMIT 1
                """, (user_id, name))
                row = cursor.fetchone()
                return row[0] if row else None
    except Exception as e:
        logging.error(f"❌ 查找 Character 失败: {e}")
        return None


def get_entity_parent_id(entity_type: str, entity_id: int) -> Optional[int]:
    """获取实体的父级 ID"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                if entity_type == 'T':
                    cursor.execute("SELECT parent_stage_id FROM topic WHERE topic_id = %s", (entity_id,))
                elif entity_type == 'O':
                    cursor.execute("SELECT parent_topic_id FROM shot WHERE shot_id = %s", (entity_id,))
                elif entity_type == 'C':
                    cursor.execute("SELECT related_shot_id FROM character WHERE character_id = %s", (entity_id,))
                else:
                    return None
                
                row = cursor.fetchone()
                return row[0] if row else None
    except Exception as e:
        logging.error(f"❌ 获取父级 ID 失败: {e}")
        return None


# ============================================================================
# 向后兼容函数（供旧版 main.py 调用）
# ============================================================================

def get_latest_hint(user_id: str) -> str:
    """
    获取最新的导演提示
    
    向后兼容函数，供旧版 main.py /ws/chat 端点使用。
    在 v3.3 中，Hint 存储在 narration_status.hint_content 中。
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # 尝试从 narration_status 获取
                cursor.execute("""
                    SELECT hint_content 
                    FROM narration_status 
                    WHERE user_id = %s 
                    LIMIT 1
                """, (user_id,))
                result = cursor.fetchone()
                if result and result[0]:
                    return result[0]
                
                # 如果失败，尝试旧表
                cursor.execute("""
                    SELECT hint_content 
                    FROM hint_board 
                    WHERE user_id = %s 
                    ORDER BY created_time DESC 
                    LIMIT 1
                """, (user_id,))
                result = cursor.fetchone()
                return result[0] if result else ""
    except Exception as e:
        logging.error(f"❌ 获取最新 Hint 失败: {e}")
        return ""


def get_previous_dialogues(user_id: str, limit: int = 5) -> str:
    """
    获取最近 N 轮对话文本内容用于 pc (previous_content)
    
    向后兼容函数，供旧版 main.py /ws/chat 端点使用。
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # 获取最近的对话记录，speaker_type 0=U, 1=I
                # 按时间倒序取 limit*2 条，然后正序拼接
                cursor.execute("""
                    SELECT speaker_type, original_text 
                    FROM interview_original_text 
                    WHERE user_id = %s 
                    ORDER BY created_time DESC 
                    LIMIT %s
                """, (user_id, limit * 2))
                rows = cursor.fetchall()
                
                # 倒序排列，变回正序
                dialogues = []
                for speaker_type, text in reversed(rows):
                    prefix = "U:" if speaker_type == 0 else "I:"
                    dialogues.append(f"{prefix}{text}")
                
                return "; ".join(dialogues)
    except Exception as e:
        logging.error(f"❌ 获取前情提要失败: {e}")
        return ""


def insert_hint_board(user_id: str, content: str) -> Optional[int]:
    """
    插入导演提示板记录
    
    向后兼容函数。
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO hint_board (user_id, hint_content)
                    VALUES (%s, %s)
                    RETURNING hint_id
                """, (user_id, content))
                hint_id = cursor.fetchone()[0]
                conn.commit()
                logging.info(f"✅ HintBoard 插入成功: {hint_id} (User: {user_id})")
                return hint_id
    except Exception as e:
        logging.error(f"❌ HintBoard 插入失败: {e}")
        return None


def update_storyboard_dir_processed(user_id: str, status: int = 1):
    """
    更新故事板导演处理状态
    
    向后兼容函数。
    在 v3.3 中使用 mark_storyboards_dir_processed 替代。
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE storyboard 
                    SET dir_processed_status = %s 
                    WHERE user_id = %s AND dir_processed_status = 0
                """, (status, user_id))
                conn.commit()
                logging.info(f"✅ StoryBoard 导演处理状态更新成功: {user_id} -> {status}")
    except Exception as e:
        logging.error(f"❌ StoryBoard 导演处理状态更新失败: {e}")
