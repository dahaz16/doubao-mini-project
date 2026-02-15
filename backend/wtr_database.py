# -*- coding: utf-8 -*-
"""
============================================================================
Writing Database Service (写作功能数据库操作层)
============================================================================

为 memoir_chapter 和 memoir_article 表提供 CRUD 操作

基于《我的故事页需求文档 v0.5.md》实现
"""

import logging
from typing import Optional, List, Dict
from .database import get_db_connection

logger = logging.getLogger(__name__)


# ============================================================================
# Memoir Chapter Operations
# ============================================================================

def get_or_create_chapter(
    user_id: str,
    link_stage_id: int,
    chapter_name: str
) -> Optional[int]:
    """
    获取或创建回忆录章节
    
    Args:
        user_id: 用户 ID
        link_stage_id: 关联的 stage_id
        chapter_name: 章节名称（通常使用 stage_title）
        
    Returns:
        int: chapter_id
        None: 创建失败
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # 检查是否已存在
                cursor.execute("""
                    SELECT chapter_id
                    FROM memoir_chapter
                    WHERE user_id = %s AND link_stage_id = %s
                """, (user_id, link_stage_id))
                
                result = cursor.fetchone()
                if result:
                    return result[0]
                
                # 不存在则创建
                # 计算 chapter_sort_num（当前用户的最大值 + 1）
                cursor.execute("""
                    SELECT COALESCE(MAX(chapter_sort_num), 0) + 1
                    FROM memoir_chapter
                    WHERE user_id = %s
                """, (user_id,))
                
                chapter_sort_num = cursor.fetchone()[0]
                
                cursor.execute("""
                    INSERT INTO memoir_chapter 
                    (link_stage_id, chapter_name, chapter_sort_num, user_id, created_time)
                    VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
                    RETURNING chapter_id
                """, (link_stage_id, chapter_name, chapter_sort_num, user_id))
                
                chapter_id = cursor.fetchone()[0]
                conn.commit()
                
                logger.info(f"✓ Created memoir_chapter: chapter_id={chapter_id}, "
                           f"stage_id={link_stage_id}, name=\"{chapter_name}\"")
                return chapter_id
                
    except Exception as e:
        logger.error(f"✗ Failed to get/create chapter for stage {link_stage_id}: {e}")
        return None


def get_chapters_by_user(user_id: str) -> List[Dict]:
    """
    获取用户的所有回忆录章节
    
    Args:
        user_id: 用户 ID
        
    Returns:
        list: [{
            'chapter_id': int,
            'link_stage_id': int,
            'chapter_name': str,
            'chapter_sort_num': int,
            'created_time': datetime
        }]
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT chapter_id, link_stage_id, chapter_name, 
                           chapter_sort_num, created_time
                    FROM memoir_chapter
                    WHERE user_id = %s
                    ORDER BY chapter_sort_num ASC
                """, (user_id,))
                
                chapters = []
                for row in cursor.fetchall():
                    chapters.append({
                        'chapter_id': row[0],
                        'link_stage_id': row[1],
                        'chapter_name': row[2],
                        'chapter_sort_num': row[3],
                        'created_time': row[4]
                    })
                
                return chapters
                
    except Exception as e:
        logger.error(f"✗ Failed to get chapters for user {user_id}: {e}")
        return []


# ============================================================================
# Memoir Article Operations
# ============================================================================

def insert_or_update_article(
    topic_id: int,
    user_id: str,
    chapter_id: int,
    section_name: str,
    section_content: str
) -> Optional[int]:
    """
    插入或更新回忆录文章
    
    如果 topic_id 已存在文章，则更新内容；否则新建
    
    Args:
        topic_id: Topic ID
        user_id: 用户 ID
        chapter_id: 章节 ID
        section_name: 小节名称（使用 topic_title）
        section_content: 文章内容
        
    Returns:
        int: section_id
        None: 操作失败
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # 检查是否已存在
                cursor.execute("""
                    SELECT section_id
                    FROM memoir_article
                    WHERE topic_id = %s
                """, (topic_id,))
                
                result = cursor.fetchone()
                
                if result:
                    # 更新现有文章
                    section_id = result[0]
                    cursor.execute("""
                        UPDATE memoir_article
                        SET section_content = %s,
                            section_name = %s,
                            chapter_id = %s
                        WHERE section_id = %s
                    """, (section_content, section_name, chapter_id, section_id))
                    
                    conn.commit()
                    logger.info(f"✓ Updated memoir_article: section_id={section_id}, topic_id={topic_id}")
                    return section_id
                else:
                    # 新建文章
                    # 计算 section_sort_num（当前 chapter 下的最大值 + 1）
                    cursor.execute("""
                        SELECT COALESCE(MAX(section_sort_num), 0) + 1
                        FROM memoir_article
                        WHERE chapter_id = %s
                    """, (chapter_id,))
                    
                    section_sort_num = cursor.fetchone()[0]
                    
                    cursor.execute("""
                        INSERT INTO memoir_article 
                        (topic_id, user_id, chapter_id, section_name, 
                         section_content, section_sort_num, created_time)
                        VALUES (%s, %s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                        RETURNING section_id
                    """, (topic_id, user_id, chapter_id, section_name, 
                          section_content, section_sort_num))
                    
                    section_id = cursor.fetchone()[0]
                    conn.commit()
                    
                    logger.info(f"✓ Created memoir_article: section_id={section_id}, "
                               f"topic_id={topic_id}, chapter_id={chapter_id}")
                    return section_id
                    
    except Exception as e:
        logger.error(f"✗ Failed to insert/update article for topic {topic_id}: {e}")
        return None


def get_articles_by_chapter(chapter_id: int) -> List[Dict]:
    """
    获取指定章节下的所有文章
    
    Args:
        chapter_id: 章节 ID
        
    Returns:
        list: [{
            'section_id': int,
            'topic_id': int,
            'section_name': str,
            'section_content': str,
            'section_sort_num': int,
            'created_time': datetime
        }]
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT section_id, topic_id, section_name, section_content,
                           section_sort_num, created_time
                    FROM memoir_article
                    WHERE chapter_id = %s
                    ORDER BY section_sort_num ASC
                """, (chapter_id,))
                
                articles = []
                for row in cursor.fetchall():
                    articles.append({
                        'section_id': row[0],
                        'topic_id': row[1],
                        'section_name': row[2],
                        'section_content': row[3],
                        'section_sort_num': row[4],
                        'created_time': row[5]
                    })
                
                return articles
                
    except Exception as e:
        logger.error(f"✗ Failed to get articles for chapter {chapter_id}: {e}")
        return []


def get_all_articles_by_user(user_id: str) -> List[Dict]:
    """
    获取用户的所有回忆录文章（按章节和小节排序）
    
    Args:
        user_id: 用户 ID
        
    Returns:
        list: [{
            'section_id': int,
            'topic_id': int,
            'chapter_id': int,
            'chapter_name': str,
            'section_name': str,
            'section_content': str,
            'chapter_sort_num': int,
            'section_sort_num': int
        }]
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        ma.section_id,
                        ma.topic_id,
                        ma.chapter_id,
                        mc.chapter_name,
                        ma.section_name,
                        ma.section_content,
                        mc.chapter_sort_num,
                        ma.section_sort_num
                    FROM memoir_article ma
                    JOIN memoir_chapter mc ON ma.chapter_id = mc.chapter_id
                    WHERE ma.user_id = %s
                    ORDER BY mc.chapter_sort_num ASC, ma.section_sort_num ASC
                """, (user_id,))
                
                articles = []
                for row in cursor.fetchall():
                    articles.append({
                        'section_id': row[0],
                        'topic_id': row[1],
                        'chapter_id': row[2],
                        'chapter_name': row[3],
                        'section_name': row[4],
                        'section_content': row[5],
                        'chapter_sort_num': row[6],
                        'section_sort_num': row[7]
                    })
                
                return articles
                
    except Exception as e:
        logger.error(f"✗ Failed to get all articles for user {user_id}: {e}")
        return []


def check_has_articles(user_id: str) -> bool:
    """
    检查用户是否已有回忆录文章
    
    Args:
        user_id: 用户 ID
        
    Returns:
        bool: True=有文章, False=无文章
    """
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT EXISTS(
                        SELECT 1 FROM memoir_article WHERE user_id = %s
                    )
                """, (user_id,))
                
                return cursor.fetchone()[0]
                
    except Exception as e:
        logger.error(f"✗ Failed to check articles for user {user_id}: {e}")
        return False
