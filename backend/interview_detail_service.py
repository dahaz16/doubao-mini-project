#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用户采访详情查询服务
提供管理后台查询用户采访记录的详细数据
"""

import logging
from typing import List, Optional, Dict, Any
from datetime import datetime
from .database import get_db_connection

logging.basicConfig(level=logging.INFO)


def get_user_interview_details(
    user_id: str,
    data_types: Optional[List[str]] = None,
    start_time: Optional[datetime] = None,
    end_time: Optional[datetime] = None,
    page: int = 1,
    page_size: int = 50
) -> Dict[str, Any]:
    """
    获取用户采访详情列表
    
    Args:
        user_id: 用户ID
        data_types: 数据方类型筛选（user, intv_output, intv_input, stn_input, stn_output, dir_input, dir_output）
        start_time: 开始时间
        end_time: 结束时间
        page: 页码（从1开始）
        page_size: 每页条数
    
    Returns:
        {
            "total": 总记录数,
            "page": 当前页码,
            "page_size": 每页条数,
            "records": [记录列表]
        }
    """
    # 默认查询所有类型
    if not data_types:
        data_types = ["user", "intv_output", "intv_input", "stn_input", "stn_output", "dir_input", "dir_output"]
    
    # 构建 UNION 查询
    union_queries = []
    params = []
    
    # 1. 用户输入（啊拓）
    if "user" in data_types:
        union_queries.append("""
            SELECT 
                'user' as data_type,
                CAST(t.interview_original_text_id AS TEXT) as record_id,
                t.created_time,
                t.original_text as content,
                t.has_voice,
                NULL::TEXT as model_name,
                NULL::INTEGER as total_tokens,
                NULL::INTEGER as prompt_tokens,
                NULL::INTEGER as completion_tokens,
                NULL::INTEGER as cached_tokens,
                NULL::TEXT as llm_input,
                NULL::TEXT as llm_output,
                NULL::TEXT as agent,
                u.user_name
            FROM interview_original_text t
            LEFT JOIN users u ON t.user_id = u.user_id
            WHERE t.user_id = %s AND t.speaker_type = 0
        """)
        params.append(user_id)
    
    # 2. AI 输出（念念）
    if "intv_output" in data_types:
        union_queries.append("""
            SELECT 
                'intv_output' as data_type,
                CAST(t.interview_original_text_id AS TEXT) as record_id,
                t.created_time,
                t.original_text as content,
                t.has_voice,
                NULL::TEXT as model_name,
                NULL::INTEGER as total_tokens,
                NULL::INTEGER as prompt_tokens,
                NULL::INTEGER as completion_tokens,
                NULL::INTEGER as cached_tokens,
                NULL::TEXT as llm_input,
                NULL::TEXT as llm_output,
                NULL::TEXT as agent,
                u.user_name
            FROM interview_original_text t
            LEFT JOIN users u ON t.user_id = u.user_id
            WHERE t.user_id = %s AND t.speaker_type = 1
        """)
        params.append(user_id)
    
    # 3. Intv LLM 输入
    if "intv_input" in data_types:
        union_queries.append("""
            SELECT 
                'intv_input' as data_type,
                CAST(p.model_processed_id AS TEXT) as record_id,
                p.created_time,
                p.input as content,
                FALSE as has_voice,
                p.model_name_cn as model_name,
                p.total_tokens,
                p.prompt_tokens,
                p.completion_tokens,
                p.cached_tokens,
                p.input as llm_input,
                p.output as llm_output,
                p.agent,
                u.user_name
            FROM llm_processed p
            LEFT JOIN users u ON p.user_id = u.user_id
            WHERE p.user_id = %s AND p.agent = 'Intv' AND p.input IS NOT NULL
        """)
        params.append(user_id)
    
    # 4. Stn LLM 输入
    if "stn_input" in data_types:
        union_queries.append("""
            SELECT 
                'stn_input' as data_type,
                CAST(p.model_processed_id AS TEXT) as record_id,
                p.created_time,
                p.input as content,
                FALSE as has_voice,
                p.model_name_cn as model_name,
                p.total_tokens,
                p.prompt_tokens,
                p.completion_tokens,
                p.cached_tokens,
                p.input as llm_input,
                p.output as llm_output,
                p.agent,
                u.user_name
            FROM llm_processed p
            LEFT JOIN users u ON p.user_id = u.user_id
            WHERE p.user_id = %s AND p.agent = 'Stn' AND p.input IS NOT NULL
        """)
        params.append(user_id)
    
    # 5. Stn LLM 输出
    if "stn_output" in data_types:
        union_queries.append("""
            SELECT 
                'stn_output' as data_type,
                CAST(p.model_processed_id AS TEXT) as record_id,
                p.created_time,
                p.output as content,
                FALSE as has_voice,
                p.model_name_cn as model_name,
                p.total_tokens,
                p.prompt_tokens,
                p.completion_tokens,
                p.cached_tokens,
                p.input as llm_input,
                p.output as llm_output,
                p.agent,
                u.user_name
            FROM llm_processed p
            LEFT JOIN users u ON p.user_id = u.user_id
            WHERE p.user_id = %s AND p.agent = 'Stn' AND p.output IS NOT NULL
        """)
        params.append(user_id)
    
    # 6. Dir LLM 输入
    if "dir_input" in data_types:
        union_queries.append("""
            SELECT 
                'dir_input' as data_type,
                CAST(p.model_processed_id AS TEXT) as record_id,
                p.created_time,
                p.input as content,
                FALSE as has_voice,
                p.model_name_cn as model_name,
                p.total_tokens,
                p.prompt_tokens,
                p.completion_tokens,
                p.cached_tokens,
                p.input as llm_input,
                p.output as llm_output,
                p.agent,
                u.user_name
            FROM llm_processed p
            LEFT JOIN users u ON p.user_id = u.user_id
            WHERE p.user_id = %s AND p.agent = 'Dir' AND p.input IS NOT NULL
        """)
        params.append(user_id)
    
    # 7. Dir LLM 输出（导演提示）
    if "dir_output" in data_types:
        union_queries.append("""
            SELECT 
                'dir_output' as data_type,
                CAST(p.model_processed_id AS TEXT) as record_id,
                p.created_time,
                p.output as content,
                FALSE as has_voice,
                p.model_name_cn as model_name,
                p.total_tokens,
                p.prompt_tokens,
                p.completion_tokens,
                p.cached_tokens,
                p.input as llm_input,
                p.output as llm_output,
                p.agent,
                u.user_name
            FROM llm_processed p
            LEFT JOIN users u ON p.user_id = u.user_id
            WHERE p.user_id = %s AND p.agent = 'Dir' AND p.output IS NOT NULL
        """)
        params.append(user_id)
    
    if not union_queries:
        return {"total": 0, "page": page, "page_size": page_size, "records": []}
    
    # 合并查询
    base_query = " UNION ALL ".join(union_queries)
    
    # 添加时间筛选
    time_filter = ""
    if start_time:
        time_filter += " AND created_time >= %s"
        params.append(start_time)
    if end_time:
        time_filter += " AND created_time <= %s"
        params.append(end_time)
    
    # 完整查询（带时间筛选和排序）
    full_query = f"""
        SELECT * FROM ({base_query}) as combined
        WHERE 1=1 {time_filter}
        ORDER BY created_time DESC
    """
    
    # 计算总数 (包裹在子查询中)
    count_query = f"SELECT COUNT(*) FROM ({full_query}) as total_count"
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # 获取总数
            cursor.execute(count_query, params)
            total = cursor.fetchone()[0]
            # 分页查询
            offset = (page - 1) * page_size
            paginated_query = full_query + f" LIMIT {page_size} OFFSET {offset}"
            
            cursor.execute(paginated_query, params)
            rows = cursor.fetchall()
            
            # 获取所有涉及的 Text ID
            text_ids = [int(row[1]) for row in rows if row[1] and str(row[1]).isdigit()]
            
            # 批量获取音频映射
            audio_map = {}
            if text_ids:
                with conn.cursor() as cursor_voice:
                    cursor_voice.execute("""
                        SELECT link_original_text_id, original_voice_url
                        FROM interview_original_voice
                        WHERE link_original_text_id = ANY(%s)
                    """, (text_ids,))
                    for v_row in cursor_voice.fetchall():
                        audio_map[v_row[0]] = v_row[1]

            # 格式化记录
            records = []
            for row in rows:
                record = _format_record_optimized(row, user_id, audio_map, conn)
                records.append(record)
            
            return {
                "total": total,
                "page": page,
                "page_size": page_size,
                "records": records
            }


def _format_record_optimized(row: tuple, user_id: str, audio_map: dict, conn) -> Dict[str, Any]:
    """优化后的格式化单条记录"""
    data_type = row[0]
    record_id = row[1]
    created_time = row[2]
    content = row[3]
    has_voice = row[4]
    model_name = row[5]
    total_tokens = row[6]
    prompt_tokens = row[7]
    completion_tokens = row[8]
    cached_tokens = row[9]
    llm_input = row[10]
    llm_output = row[11]
    agent = row[12]
    user_name = row[13] if len(row) > 13 else None
    
    # 格式化日期和时间
    date_str = created_time.strftime("%Y-%m-%d") if created_time else ""
    time_str = created_time.strftime("%H:%M:%S") if created_time else ""
    
    # 获取音频链接
    audio_url = None
    if has_voice:
        text_id = int(record_id) if record_id and str(record_id).isdigit() else None
        # 1. 优先从预取的 map 中找
        if text_id and text_id in audio_map:
            audio_url = audio_map[text_id]
        else:
            # 2. 兜底逻辑：时间相似度匹配
            audio_url = _get_audio_url_simple(conn, user_id, created_time, data_type)
    
    # 格式化内容
    content_str = str(content) if content else ""
    is_long = len(content_str) > 50
    content_preview = content_str[:50] + "..." if is_long else content_str
    
    # 判断是否为 JSON 内容
    is_json = isinstance(content, (dict, list)) or (isinstance(content, str) and content.strip().startswith('{'))
    
    # 格式化 Tokens
    tokens_str = ""
    if total_tokens is not None:
        tokens_str = f"{total_tokens} (prt:{prompt_tokens or 0}, cp:{completion_tokens or 0}, cch:{cached_tokens or 0})"
    
    # 获取 Session ID
    session_id = _get_session_id(conn, user_id, agent)
    
    # 获取 Prompt 信息
    prompt_str = _get_prompt_info(conn, agent) if agent else ""
    
    return {
        "data_type": data_type,
        "user_name": user_name or "未知用户",
        "date": date_str,
        "time": time_str,
        "has_audio": has_voice,
        "audio_url": audio_url,
        "content": content_str if not is_json else None,
        "content_preview": content_preview,
        "full_content": {"input": llm_input, "output": llm_output} if llm_input or llm_output else content,
        "is_json": is_json,
        "is_long": is_long,
        "session_id": session_id,
        "model_name": model_name or "-",
        "tokens": tokens_str or "-",
        "prompt": prompt_str or "-",
        "record_id": f"{data_type}_{record_id}"
    }


def _get_audio_url_simple(conn, user_id: str, created_time: datetime, data_type: str) -> Optional[str]:
    """简单的时间匹配关联音频"""
    speaker_type = 0 if data_type == "user" else 1
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT original_voice_url
            FROM interview_original_voice
            WHERE user_id = %s 
              AND speaker_type = %s
              AND ABS(EXTRACT(EPOCH FROM (created_time - %s))) < 15
            ORDER BY ABS(EXTRACT(EPOCH FROM (created_time - %s)))
            LIMIT 1
        """, (user_id, speaker_type, created_time, created_time))
        row = cursor.fetchone()
        return row[0] if row else None


def _get_session_id(conn, user_id: str, agent: Optional[str]) -> str:
    """获取 Session ID"""
    if not agent:
        return "-"
    
    session_field_map = {
        "Intv": "intv_llm_session_id",
        "Stn": "stn_llm_session_id",
        "Dir": "dir_llm_session_id"
    }
    
    field = session_field_map.get(agent)
    if not field:
        return "-"
    
    with conn.cursor() as cursor:
        cursor.execute(f"""
            SELECT {field}
            FROM narration_status
            WHERE user_id = %s
        """, (user_id,))
        
        row = cursor.fetchone()
        return str(row[0]) if row and row[0] else "-"


def _get_prompt_info(conn, agent: str) -> str:
    """获取 Prompt 信息"""
    llm_type_map = {
        "Intv": 0,
        "Stn": 1,
        "Dir": 2
    }
    
    llm_type = llm_type_map.get(agent)
    if llm_type is None:
        return "-"
    
    with conn.cursor() as cursor:
        cursor.execute("""
            SELECT prompt_id, llm_type
            FROM prompt_config
            WHERE llm_type = %s AND is_active = TRUE
            LIMIT 1
        """, (llm_type,))
        
        row = cursor.fetchone()
        if row:
            llm_type_names = {0: "Intv", 1: "Stn", 2: "Dir"}
            return f"{row[0]} ({llm_type_names.get(row[1], 'Unknown')})"
        return "-"
