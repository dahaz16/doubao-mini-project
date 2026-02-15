# -*- coding: utf-8 -*-
"""
============================================================================
Wtr Service (写作 Agent 服务)
============================================================================

Wtr Agent 核心服务，负责：
1. 写作时机判断
2. 组装 LLM 输入（reference_article + writing_source）
3. 调用 Wtr LLM
4. 解析 JSON 输出
5. 创建/更新 memoir_chapter 和 memoir_article
6. 状态回滚与清理

基于《我的故事页需求文档 v0.5.md》实现
"""

import json
import logging
from typing import Optional, Dict, List
from .database import get_db_connection
from .config_manager import ConfigManager
from .wtr_cachepool_service import get_writing_status, get_pending_topics, clear_cachepool
from .wtr_database import (
    get_or_create_chapter,
    insert_or_update_article,
    check_has_articles,
    get_all_articles_by_user
)

# Use logging directly for consistency with other services
# logger = logging.getLogger(__name__)


def check_writing_readiness(user_id: str) -> Dict:
    """
    写作时机判断
    
    Args:
        user_id: 用户 ID
        
    Returns:
        dict: {
            'ready': bool,  # 是否可以写作
            'is_first_time': bool,  # 是否首次写作
            'words_count': int,  # 当前缓存池字数
            'threshold': int  # 触发阈值
        }
    """
    config_mgr = ConfigManager()
    threshold = int(config_mgr.get_config('wtr_cache_pool_limit', 500))
    
    # 获取写作状态
    status = get_writing_status(user_id)
    if not status:
        return {
            'ready': False,
            'is_first_time': True,
            'words_count': 0,
            'threshold': threshold
        }
    
    words_count = status['cachepool_words_count']
    writing_state = status['writing_state']
    
    # 检查是否已有文章
    has_articles = check_has_articles(user_id)
    
    # 写作时机判断逻辑
    # 首次和非首次都需要达到阈值
    ready = words_count >= threshold
    
    # 如果正在写作中，不允许再次触发
    if writing_state == 1:
        ready = False
    
    return {
        'ready': ready,
        'is_first_time': not has_articles,
        'words_count': words_count,
        'threshold': threshold
    }


def _build_reference_article(user_id: str, pending_topics: List[Dict]) -> str:
    """
    组装前情提要（reference_article）
    
    按 PRD 逻辑：
    1. 提取所有 pending_topic 的 parent_stage_id（去重）
    2. 按 parent_stage_id → memoir_chapter → memoir_article 查询
    3. 拼接格式：章节名 + 文章名 + 内容
    4. 超过 wtr_reference_words_limit 时截断
    
    Args:
        user_id: 用户 ID
        pending_topics: 待写作的 topic 列表
        
    Returns:
        str: 前情提要文本
    """
    config_mgr = ConfigManager()
    word_limit = int(config_mgr.get_config('wtr_reference_words_limit', 3000))
    
    # 提取所有 parent_stage_id（去重）
    stage_ids = list(set(
        topic['parent_stage_id'] 
        for topic in pending_topics 
        if topic['parent_stage_id']
    ))
    
    if not stage_ids:
        return ""
    
    # 查询这些 stage 对应的 chapter 和 article
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT 
                        mc.chapter_name,
                        ma.section_name,
                        ma.section_content,
                        mc.chapter_sort_num,
                        ma.section_sort_num
                    FROM memoir_chapter mc
                    JOIN memoir_article ma ON mc.chapter_id = ma.chapter_id
                    WHERE mc.user_id = %s AND mc.link_stage_id = ANY(%s)
                    ORDER BY mc.chapter_sort_num ASC, ma.section_sort_num ASC
                """, (user_id, stage_ids))
                
                articles = cursor.fetchall()
                
                # 拼接文本
                reference_parts = []
                total_words = 0
                
                for chapter_name, section_name, section_content, _, _ in articles:
                    part = f"【{chapter_name}】{section_name}\n{section_content}\n\n"
                    part_words = len(part)
                    
                    if total_words + part_words > word_limit:
                        # 超限，截断
                        remaining = word_limit - total_words
                        if remaining > 0:
                            reference_parts.append(part[:remaining] + "...")
                        break
                    
                    reference_parts.append(part)
                    total_words += part_words
                
                return "".join(reference_parts).strip()
                
    except Exception as e:
        logging.error(f"✗ Failed to build reference_article: {e}")
        return ""


def _build_writing_source(pending_topics: List[Dict]) -> str:
    """
    组装写作素材（writing_source）
    
    格式：[{topic_id}]{topic_title}-{topic_content}
    按 topic_id 升序
    
    Args:
        pending_topics: 待写作的 topic 列表
        
    Returns:
        str: 写作素材文本
    """
    parts = []
    for topic in sorted(pending_topics, key=lambda x: x['topic_id']):
        topic_id = topic['topic_id']
        title = topic['topic_title'] or ""
        content = topic['topic_content'] or ""
        parts.append(f"[{topic_id}]{title}-{content}")
    
    return "\n".join(parts)


async def run_wtr_agent(user_id: str) -> Dict:
    """
    Wtr Agent 写作主流程
    
    Args:
        user_id: 用户 ID
        
    Returns:
        dict: {
            'success': bool,
            'message': str,
            'articles_created': int,  # 成功创建的文章数
            'error': str  # 错误信息（如果失败）
        }
    """
    from .llm_api_service import call_wtr_llm, record_llm_usage
    
    logging.info(f"🚀 Starting Wtr Agent for user {user_id}")
    
    try:
        # Step 1: 获取 pending topics
        pending_topics = get_pending_topics(user_id)
        if not pending_topics:
            return {
                'success': False,
                'message': '缓存池为空，无待写作内容',
                'articles_created': 0
            }
        
        pending_topic_ids = [t['topic_id'] for t in pending_topics]
        logging.info(f"  Pending topics: {pending_topic_ids}")
        
        # Step 2: 更新状态为 writing
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # 更新 writing_status.writing_state = 1
                cursor.execute("""
                    UPDATE writing_status
                    SET writing_state = 1,
                        updated_time = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                """, (user_id,))
                
                # 更新所有 pending_topic 的 topic_writing_state = 1
                cursor.execute("""
                    UPDATE topic
                    SET topic_writing_state = 1
                    WHERE topic_id = ANY(%s)
                """, (pending_topic_ids,))
                
                conn.commit()
        
        logging.info(f"  ✓ Updated writing_state to 1 (writing)")
        
        # Step 3: 组装 reference_article
        reference_article = _build_reference_article(user_id, pending_topics)
        logging.info(f"  ✓ Built reference_article: {len(reference_article)} chars")
        
        # Step 4: 组装 writing_source
        writing_source = _build_writing_source(pending_topics)
        logging.info(f"  ✓ Built writing_source: {len(writing_source)} chars")
        
        # Step 5: 构建 wtr_llm_input
        config_mgr = ConfigManager()
        wtr_prompt = config_mgr.get_active_prompt(llm_type=3)
        
        if not wtr_prompt:
            raise Exception("Wtr prompt not found (llm_type=3)")
        
        input_messages = [
            {"role": "system", "content": wtr_prompt},
            {"role": "assistant", "content": f"前情提要:{reference_article}"},
            {"role": "user", "content": f"本次写作素材:{writing_source}"}
        ]
        
        logging.info(f"  ✓ Built wtr_llm_input with {len(input_messages)} messages")
        
        # Step 6: 调用 Wtr LLM（含重试逻辑）
        max_retries = 2
        llm_response = None
        parsed_data = None
        
        for attempt in range(max_retries + 1):
            try:
                logging.info(f"  🤖 Calling Wtr LLM (attempt {attempt + 1}/{max_retries + 1})...")
                
                llm_response = await call_wtr_llm(
                    user_id=user_id,
                    input_messages=input_messages,
                    llm_input_str=writing_source[:200]  # 记录前 200 字符
                )
                
                # Step 7: JSON 解析
                response_text = llm_response.get('content', '')
                parsed_data = json.loads(response_text)
                
                # 验证 JSON 结构
                if 'articles' not in parsed_data or not isinstance(parsed_data['articles'], list):
                    raise ValueError("Invalid JSON structure: missing 'articles' array")
                
                logging.info(f"  ✓ LLM response parsed successfully: {len(parsed_data['articles'])} articles")
                break
                
            except json.JSONDecodeError as e:
                logging.warning(f"  ⚠️  JSON parse error (attempt {attempt + 1}): {e}")
                if attempt == max_retries:
                    raise Exception(f"JSON parsing failed after {max_retries + 1} attempts")
            except Exception as e:
                logging.warning(f"  ⚠️  LLM call error (attempt {attempt + 1}): {e}")
                if attempt == max_retries:
                    raise
        
        # Step 8: 失败回滚（如果到这里说明成功了，跳过）
        
        # Step 9: 成功处理 - 遍历 articles 数组
        articles_created = 0
        
        for article_data in parsed_data['articles']:
            topic_id = article_data.get('topic_id')
            article_content = article_data.get('article_content', '')
            
            if not topic_id or not article_content:
                logging.warning(f"  ⚠️  Skipping invalid article: {article_data}")
                continue
            
            # 查找对应的 topic
            topic = next((t for t in pending_topics if t['topic_id'] == topic_id), None)
            if not topic:
                logging.warning(f"  ⚠️  Topic {topic_id} not found in pending_topics")
                continue
            
            parent_stage_id = topic['parent_stage_id']
            topic_title = topic['topic_title']
            
            if not parent_stage_id:
                logging.warning(f"  ⚠️  Topic {topic_id} has no parent_stage_id, skipping")
                continue
            
            # 获取 stage_title（用作 chapter_name）
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        SELECT stage_title FROM stage WHERE stage_id = %s
                    """, (parent_stage_id,))
                    result = cursor.fetchone()
                    stage_title = result[0] if result else f"Stage {parent_stage_id}"
            
            # 判断/创建 chapter
            chapter_id = get_or_create_chapter(
                user_id=user_id,
                link_stage_id=parent_stage_id,
                chapter_name=stage_title
            )
            
            if not chapter_id:
                logging.error(f"  ✗ Failed to create chapter for stage {parent_stage_id}")
                continue
            
            # 写入/更新 article（section_name = topic_title）
            section_id = insert_or_update_article(
                topic_id=topic_id,
                user_id=user_id,
                chapter_id=chapter_id,
                section_name=topic_title,
                section_content=article_content
            )
            
            if not section_id:
                logging.error(f"  ✗ Failed to insert/update article for topic {topic_id}")
                continue
            
            # 更新 topic_writing_state = 2 (done)
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    cursor.execute("""
                        UPDATE topic
                        SET topic_writing_state = 2
                        WHERE topic_id = %s
                    """, (topic_id,))
                    conn.commit()
            
            articles_created += 1
            logging.info(f"  ✓ Article created/updated: topic_id={topic_id}, section_id={section_id}")
        
        # Step 10: 清理 cachepool
        clear_cachepool(user_id, pending_topic_ids)
        
        # 更新 writing_status.writing_state = 0
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE writing_status
                    SET writing_state = 0,
                        updated_time = CURRENT_TIMESTAMP
                    WHERE user_id = %s
                """, (user_id,))
                conn.commit()
        
        logging.info(f"  ✓ Cachepool cleared, writing_state reset to 0")
        
        # Step 11: 记录 LLM 调用
        if llm_response:
            record_llm_usage(
                user_id=user_id,
                agent='Wtr',
                llm_input=writing_source[:500],  # 记录前 500 字符
                llm_output=llm_response.get('content', '')[:500],
                input_tokens=llm_response.get('usage', {}).get('input_tokens', 0),
                output_tokens=llm_response.get('usage', {}).get('output_tokens', 0),
                total_tokens=llm_response.get('usage', {}).get('total_tokens', 0)
            )
        
        logging.info(f"🎉 Wtr Agent completed successfully: {articles_created} articles created")
        
        return {
            'success': True,
            'message': f'写作完成，共生成 {articles_created} 篇文章',
            'articles_created': articles_created
        }
        
    except Exception as e:
        logging.error(f"❌ Wtr Agent failed: {e}")
        
        # 失败回滚
        try:
            with get_db_connection() as conn:
                with conn.cursor() as cursor:
                    # 回滚 writing_status.writing_state = 0
                    cursor.execute("""
                        UPDATE writing_status
                        SET writing_state = 0,
                            updated_time = CURRENT_TIMESTAMP
                        WHERE user_id = %s
                    """, (user_id,))
                    
                    # 回滚所有 topic_writing_state = 0
                    cursor.execute("""
                        UPDATE topic
                        SET topic_writing_state = 0
                        WHERE user_id = %s AND topic_writing_state = 1
                    """, (user_id,))
                    
                    conn.commit()
            
            logging.info("  ✓ State rollback completed")
        except Exception as rollback_error:
            logging.error(f"  ✗ Rollback failed: {rollback_error}")
        
        return {
            'success': False,
            'message': '写作失败',
            'articles_created': 0,
            'error': str(e)
        }
