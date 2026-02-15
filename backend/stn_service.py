#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
Stn Service (速记员 Agent 服务) v3.3
============================================================================

速记员 Agent 完整工作流：
1. 并发控制：用户级 FIFO 队列
2. Session 处理：检查有效性，决定上下文模式
3. 构建 LLM 输入：sb + uc + cp
4. 调用 Stn LLM（JSON 模式）
5. 解析新格式 JSON（S/T/O/C/R）
6. 实体入库与关系建立
7. 写入 Storyboard
8. 更新处理状态
9. 触发 Dir Agent

根据《服务端流程文档与数据库结构设计 v3.3》实现。
"""

import asyncio
import json
import re
import logging
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime, timezone

from .narration_service import (
    get_or_create_narration_status,
    check_stn_session_valid,
    update_stn_session,
    take_cachepool_snapshot,
)
from .llm_api_service import call_stn_llm
from .database import get_db_connection
from .stn_database import (
    insert_stage, update_stage,
    insert_topic, update_topic,
    insert_shot, update_shot,
    insert_character, update_character,
    insert_storyboard,
    get_unprocessed_storyboards_for_stn,
    get_latest_storyboards,
    mark_storyboards_stn_processed,
    format_storyboards_for_llm,
    find_stage_by_title,
    find_topic_by_title,
    find_shot_by_title,
    find_character_by_name,
)
from .config_manager import get_config, get_active_prompt

logging.basicConfig(level=logging.INFO)


# ============================================================================
# 用户级并发控制（FIFO 队列）
# ============================================================================

_user_locks: Dict[str, asyncio.Lock] = {}


def _get_user_lock(user_id: str) -> asyncio.Lock:
    """获取用户级别的锁"""
    if user_id not in _user_locks:
        _user_locks[user_id] = asyncio.Lock()
    return _user_locks[user_id]


# ============================================================================
# Stn Agent 主入口
# ============================================================================

async def run_stn_agent(user_id: str) -> bool:
    """
    运行 Stn Agent
    
    这是一个异步函数，可以被 Intv Agent 在后台调用。
    使用用户级锁保证同一用户的任务按 FIFO 顺序执行。
    
    Returns:
        bool: 是否成功
    """
    lock = _get_user_lock(user_id)
    
    async with lock:
        logging.info(f"📝 Stn Agent 开始工作 (User: {user_id[:8]}...)")
        
        try:
            # Step 1: 获取缓存池快照
            cachepool_content = take_cachepool_snapshot(user_id)
            if not cachepool_content:
                logging.info("📝 Stn Agent: 缓存池为空，跳过")
                return True
            
            # Step 2: 检查 Session 有效性
            session_valid, reason = check_stn_session_valid(user_id)
            
            # Step 3: 获取 Storyboard 上下文
            if session_valid:
                # 有效时：获取未处理的 SB 记录
                sb_records = get_unprocessed_storyboards_for_stn(user_id)
                logging.info(f"📝 Stn Session 有效，获取 {len(sb_records)} 条未处理 SB")
            else:
                # 无效时：获取最新 N 条作为完整上下文
                sb_records = get_latest_storyboards(user_id)
                logging.info(f"📝 Stn Session 无效 ({reason})，获取 {len(sb_records)} 条最新 SB")
            
            sb_context = format_storyboards_for_llm(sb_records)
            
            # Step 4: 获取 Stn 未处理内容（如果有的话）
            status = get_or_create_narration_status(user_id)
            unprocessed_content = status.get('stn_unprocessed_content') or ''
            
            # 获取 previous_response_id 和 expire_at (用于 Session Caching)
            prev_response_id = status.get('stn_llm_session_previous_response_id') if session_valid else None
            expire_at_dt = status.get('stn_llm_session_expire_at') if session_valid else None
            expire_at = int(expire_at_dt.timestamp()) if expire_at_dt else None
            
            # 合并未处理内容和新内容
            user_content = (unprocessed_content + " " + cachepool_content).strip()
            
            # Step 5: 构建 LLM 输入
            llm_input = _build_stn_input(sb_context, user_content)
            
            # 序列化 llm_input 为字符串（用于记录）
            import json
            llm_input_str = json.dumps(llm_input, ensure_ascii=False)
            
            # Step 6: 调用 Stn LLM (Async) - ✅ v3.8: 传入 expire_at
            result = await call_stn_llm(
                user_id, 
                llm_input, 
                previous_response_id=prev_response_id,
                expire_at=expire_at,
                llm_input_str=llm_input_str
            )
            
            if not result.get('success'):
                logging.error(f"❌ Stn LLM 调用失败: {result.get('error')}")
                # 保存未处理内容
                update_stn_session(user_id, unprocessed_content=user_content)
                return False
            
            # Step 7: 解析 JSON 响应
            json_content = result.get('content', '')
            parsed_data = _parse_stn_response(json_content)
            
            if not parsed_data:
                logging.error(f"❌ Stn JSON 解析失败")
                update_stn_session(user_id, unprocessed_content=user_content)
                return False
            
            # Step 8: 处理解析结果，入库
            max_sb_id = await _process_parsed_data(user_id, parsed_data)
            
            # Step 9: 标记 SB 已处理，清空未处理内容
            if sb_records:
                old_max_id = max(sb['story_id'] for sb in sb_records)
                mark_storyboards_stn_processed(user_id, old_max_id)
            
            # Step 10: 更新 Session 状态 - ✅ v3.8: 存储 previous_response_id
            new_response_id = result.get('response_id')
            update_stn_session(
                user_id=user_id,
                session_id=new_response_id,
                previous_response_id=new_response_id,  # ✅ 存储 previous_response_id
                unprocessed_content=None
            )
            
            # Step 10: 触发 Dir Agent
            asyncio.create_task(_trigger_dir_agent(user_id))
            
            logging.info(f"✅ Stn Agent 完成 (User: {user_id[:8]}...)")
            return True
            
        except Exception as e:
            logging.error(f"❌ Stn Agent 异常: {e}", exc_info=True)
            return False


# ============================================================================
# 向后兼容函数（供旧版 cachepool_service 调用）
# ============================================================================

def run_stn_agent_async(user_id: str, session_id: str, cache_content: str, cachepool_id: int):
    """
    向后兼容的 Stn Agent 触发函数
    
    这个函数保持了旧版 API 签名，供 cachepool_service 调用。
    在 v3.3 中，session_id 和 cachepool_id 参数被忽略，
    因为新版使用 narration_status 表进行统一管理。
    
    Args:
        user_id: 用户 ID
        session_id: 会话 ID (v3.3 中忽略)
        cache_content: 缓存内容 (v3.3 中忽略，从 narration_status 获取)
        cachepool_id: 缓存池 ID (v3.3 中忽略)
    """
    logging.info(f"🔔 触发 Stn Agent (User: {user_id[:8]}...)")
    
    async def _run():
        try:
            logging.info(f"🚀 开始执行 Stn Agent 异步任务 (User: {user_id[:8]}...)")
            result = await run_stn_agent(user_id)
            logging.info(f"✅ Stn Agent 异步任务完成 (User: {user_id[:8]}..., Result: {result})")
        except Exception as e:
            logging.error(f"❌ run_stn_agent_async 执行失败: {e}", exc_info=True)
    
    def _task_done_callback(task):
        """异步任务完成回调,用于捕获未处理的异常"""
        try:
            task.result()  # 这会重新抛出任务中的异常
        except Exception as e:
            logging.error(f"💥 Stn Agent 异步任务异常 (User: {user_id[:8]}...): {e}", exc_info=True)
    
    # 使用 asyncio.create_task 如果在异步上下文中
    try:
        loop = asyncio.get_running_loop()
        task = asyncio.create_task(_run())
        task.add_done_callback(_task_done_callback)  # 添加回调捕获异常
        logging.info(f"📋 Stn Agent 任务已创建 (User: {user_id[:8]}...)")
    except RuntimeError:
        # 没有运行中的事件循环，创建一个新的
        logging.info(f"📋 Stn Agent 同步执行 (User: {user_id[:8]}...)")
        asyncio.run(_run())


# ============================================================================
# 构建 LLM 输入
# ============================================================================

#  ============================================================================
# v3.4: Stn System Prompt 现已从 prompt_config 表动态读取

def _build_stn_input(sb_context: str, user_content: str) -> List[Dict[str, str]]:
    """
    构建 Stn LLM 输入（v3.4）
    
    格式：sb:...; uc:...; cp:...
uc/cp 合并为 user_content，按需要拼接
    """
    # 获取 prompt
    stn_prompt = get_active_prompt(llm_type=1)
    if not stn_prompt:
        logging.warning("⚠️ 未找到 stn prompt，使用空字符串")
        stn_prompt = ""
    
    # 构造 user message
    parts = []
    if sb_context:
        parts.append(f"sb:{sb_context}")
    
    # user_content 已经包含了 uc + cp 的合并内容
    if user_content:
        parts.append(f"cp:{user_content}")
    
    user_message = "; ".join(parts) if parts else ""
    
    return [
        {"role": "system", "content": stn_prompt},
        {"role": "user", "content": user_message}
    ]


# ============================================================================
# 解析 LLM 响应 (新格式 S/T/O/C/R)
# ============================================================================

def _parse_stn_response(json_str: str) -> Optional[Dict[str, Any]]:
    """
    解析 Stn LLM 的 JSON 响应
    
    v3.6 新格式：
    {
        "type": "memory",
        "memory_content": {
            "S": [...],
            "T": [...],
            "O": [...],  
            "C": [...],
            "R": [...]
        }
    }
    
    向后兼容旧格式（直接返回 {S, T, O, C, R}）
    """
    if not json_str or not json_str.strip():
        return None
    
    try:
        # 尝试直接解析
        data = json.loads(json_str)
        
        # v3.6: 如果有 memory_content 字段,提取它
        if 'memory_content' in data:
            logging.info("📝 检测到 v3.6 格式,提取 memory_content")
            return data['memory_content']
        
        # 向后兼容:直接返回(旧格式)
        return data
        
    except json.JSONDecodeError:
        pass
    
    # 尝试提取 JSON 块
    try:
        # 匹配 ```json ... ``` 块
        match = re.search(r'```json\s*(.*?)\s*```', json_str, re.DOTALL)
        if match:
            data = json.loads(match.group(1))
            # v3.6: 提取 memory_content
            if 'memory_content' in data:
                logging.info("📝 检测到 v3.6 格式,提取 memory_content")
                return data['memory_content']
            return data
        
        # 匹配第一个 { ... } 块
        match = re.search(r'\{.*\}', json_str, re.DOTALL)
        if match:
            data = json.loads(match.group(0))
            # v3.6: 提取 memory_content
            if 'memory_content' in data:
                logging.info("📝 检测到 v3.6 格式,提取 memory_content")
                return data['memory_content']
            return data
            
    except json.JSONDecodeError as e:
        logging.error(f"❌ JSON 解析错误: {e}")
    
    return None


# ============================================================================
# 处理解析结果，实体入库
# ============================================================================

async def _process_parsed_data(user_id: str, data: Dict[str, Any]) -> Optional[int]:
    """
    处理解析后的数据，按 S -> T -> O -> C 顺序入库
    
    维护 tid -> real_id 映射表
    
    Returns:
        最大的 story_id（用于标记处理状态）
    """
    # 临时 ID -> 真实数据库 ID 映射
    id_map: Dict[str, int] = {}
    max_story_id = None
    
    # 1. 处理 Stage (S)
    stages = data.get('S', [])
    for stage in stages:
        stage_id = _process_stage(user_id, stage, id_map)
        if stage_id:
            story_id = _create_storyboard_entry(user_id, 'S', stage_id, stage)
            if story_id:
                max_story_id = story_id
    
    # 2. 处理 Topic (T)
    topics = data.get('T', [])
    for topic in topics:
        topic_id = _process_topic(user_id, topic, id_map)
        if topic_id:
            story_id = _create_storyboard_entry(user_id, 'T', topic_id, topic)
            if story_id:
                max_story_id = story_id
    
    # 3. 处理 Shot (O) - ❌ v3.0: 已移除 Shot 实体
    # shots = data.get('O', [])
    # for shot in shots:
    #     shot_id = _process_shot(user_id, shot, id_map)
    #     if shot_id:
    #         story_id = _create_storyboard_entry(user_id, 'O', shot_id, shot)
    #         if story_id:
    #             max_story_id = story_id
    
    # 4. 处理 Character (C)
    characters = data.get('C', [])
    for char in characters:
        char_id = _process_character(user_id, char, id_map)
        if char_id:
            story_id = _create_storyboard_entry(user_id, 'C', char_id, char)
            if story_id:
                max_story_id = story_id
    
    # 5. 处理关系 (R)
    relations = data.get('R', [])
    for rel in relations:
        _process_relation(user_id, rel, id_map)
    
    logging.info(f"📝 处理完成: S={len(stages)}, T={len(topics)}, C={len(characters)}, R={len(relations)}")
    
    return max_story_id


def _process_stage(user_id: str, stage: Dict[str, Any], id_map: Dict[str, int]) -> Optional[int]:
    """处理 Stage 实体"""
    pt = stage.get('pt', 'n')
    tid = stage.get('tid')
    
    if pt == 'n':
        # 新建
        stage_id = insert_stage(
            user_id=user_id,
            title=stage.get('title', ''),
            summary=stage.get('stage_summary') or stage.get('summary'),
            content=stage.get('stage_content') or stage.get('content'),
            start_time=None,  # ✅ v3.0: 强制为 None
            end_time=None     # ✅ v3.0: 强制为 None
        )
        if stage_id and tid:
            id_map[tid] = stage_id
        return stage_id
    else:
        # 更新
        stage_id = stage.get('id') or (find_stage_by_title(user_id, stage.get('title', '')) if stage.get('title') else None)
        if stage_id:
            update_stage(
                stage_id=stage_id,
                title=stage.get('title'),
                summary=stage.get('stage_summary') or stage.get('summary'),
                content=stage.get('stage_content') or stage.get('content')
            )
            if tid:
                id_map[tid] = stage_id
        return stage_id


def _process_topic(user_id: str, topic: Dict[str, Any], id_map: Dict[str, int]) -> Optional[int]:
    """处理 Topic 实体（两阶段处理：先插入，后建立关系）"""
    from .wtr_cachepool_service import update_writing_cachepool
    
    pt = topic.get('pt', 'n')
    tid = topic.get('tid')
    
    if pt == 'n':
        # 新建 - 不设置父级外键，由 R 数组处理
        topic_id = insert_topic(
            user_id=user_id,
            title=topic.get('title', ''),
            summary=topic.get('topic_summary') or topic.get('summary'),
            content=topic.get('topic_content') or topic.get('content'),
            parent_stage_id=None  # 阶段 1：不设置父级
        )
        if topic_id:
            # ✅ v0.5: 新增 topic 后，设置 topic_writing_state = 0 并触发写作缓存池更新
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("""
                            UPDATE topic
                            SET topic_writing_state = 0
                            WHERE topic_id = %s
                        """, (topic_id,))
                        conn.commit()
                
                # 触发写作缓存池更新
                update_writing_cachepool(user_id, topic_id)
            except Exception as e:
                logging.warning(f"⚠️  Failed to update writing cachepool for topic {topic_id}: {e}")
            
            if tid:
                id_map[tid] = topic_id
        return topic_id
    else:
        # 更新
        topic_id = topic.get('id') or (find_topic_by_title(user_id, topic.get('title', '')) if topic.get('title') else None)
        if topic_id:
            update_topic(
                topic_id=topic_id,
                title=topic.get('title'),
                summary=topic.get('topic_summary') or topic.get('summary'),
                content=topic.get('topic_content') or topic.get('content')
            )
            
            # ✅ v0.5: 更新 topic 后，设置 topic_writing_state = 0 并触发写作缓存池更新
            try:
                with get_db_connection() as conn:
                    with conn.cursor() as cursor:
                        cursor.execute("""
                            UPDATE topic
                            SET topic_writing_state = 0
                            WHERE topic_id = %s
                        """, (topic_id,))
                        conn.commit()
                
                # 触发写作缓存池更新
                update_writing_cachepool(user_id, topic_id)
            except Exception as e:
                logging.warning(f"⚠️  Failed to update writing cachepool for topic {topic_id}: {e}")
            
            if tid:
                id_map[tid] = topic_id
        return topic_id


def _process_shot(user_id: str, shot: Dict[str, Any], id_map: Dict[str, int]) -> Optional[int]:
    """处理 Shot 实体（两阶段处理：先插入，后建立关系）"""
    pt = shot.get('pt', 'n')
    tid = shot.get('tid')
    
    if pt == 'n':
        # 新建 - 不设置父级外键，由 R 数组处理
        shot_id = insert_shot(
            user_id=user_id,
            title=shot.get('title', ''),
            summary=shot.get('summary'),
            content=shot.get('content'),
            shot_type=shot.get('type', 1),
            parent_topic_id=None  # 阶段 1：不设置父级
        )
        if shot_id and tid:
            id_map[tid] = shot_id
        return shot_id
    else:
        # 更新
        shot_id = shot.get('id') or (find_shot_by_title(user_id, shot.get('title', '')) if shot.get('title') else None)
        if shot_id:
            update_shot(
                shot_id=shot_id,
                title=shot.get('title'),
                summary=shot.get('summary'),
                content=shot.get('content'),
                shot_type=shot.get('type')
            )
            if tid:
                id_map[tid] = shot_id
        return shot_id


def _process_character(user_id: str, char: Dict[str, Any], id_map: Dict[str, int]) -> Optional[int]:
    """处理 Character 实体（两阶段处理：先插入，后建立关系）"""
    pt = char.get('pt', 'n')
    tid = char.get('tid')
    
    if pt == 'n':
        # 新建 - 不设置关联外键，由 R 数组处理
        char_id = insert_character(
            user_id=user_id,
            name=char.get('name', ''),
            relation=char.get('relation'),
            evaluation=char.get('evaluation'),
            related_shot_id=None  # 阶段 1：不设置关联
        )
        if char_id and tid:
            id_map[tid] = char_id
        return char_id
    else:
        # 更新
        char_id = char.get('id') or (find_character_by_name(user_id, char.get('name', '')) if char.get('name') else None)
        if char_id:
            update_character(
                character_id=char_id,
                name=char.get('name'),
                relation=char.get('relation'),
                evaluation=char.get('evaluation')
            )
            if tid:
                id_map[tid] = char_id
        return char_id


def _process_relation(user_id: str, rel: Dict[str, Any], id_map: Dict[str, int]):
    """
    处理关系
    
    关系类型：
    - link: 建立父子关系
    - unlink: 解除关系
    """
    # ✅ v3.0: 防御性检查 - 忽略涉及 Shot 的关系
    src_type = _get_entity_type_from_id(rel.get('src'), id_map)
    tgt_type = _get_entity_type_from_id(rel.get('tgt'), id_map)
    
    if src_type == 'O' or tgt_type == 'O':
        logging.warning(f"⚠️ v3.0: 忽略涉及 Shot 的关系 - src={rel.get('src')}, tgt={rel.get('tgt')}")
        return
    
    rel_type = rel.get('type')
    src = _resolve_id(rel.get('src'), id_map)
    tgt = _resolve_id(rel.get('tgt'), id_map)
    
    if not src or not tgt:
        logging.warning(f"⚠️ 关系处理跳过: src={rel.get('src')}, tgt={rel.get('tgt')}")
        return
    
    if rel_type == 'link':
        # 建立父子关系
        # 需要根据 src 的类型决定更新哪个表
        src_type = _get_entity_type_from_id(rel.get('src'), id_map)
        
        if src_type == 'T':
            update_topic(src, parent_stage_id=tgt)
        elif src_type == 'O':
            update_shot(src, parent_topic_id=tgt)
        elif src_type == 'C':
            update_character(src, related_shot_id=tgt)
        
        logging.info(f"🔗 建立关系: {src} -> {tgt}")
    
    elif rel_type == 'unlink':
        # 解除关系（设置为 NULL）
        src_type = _get_entity_type_from_id(rel.get('src'), id_map)
        
        if src_type == 'T':
            update_topic(src, parent_stage_id=None)
        elif src_type == 'O':
            update_shot(src, parent_topic_id=None)
        elif src_type == 'C':
            update_character(src, related_shot_id=None)
        
        logging.info(f"🔓 解除关系: {src} -x- {tgt}")


def _resolve_id(id_ref: Any, id_map: Dict[str, int]) -> Optional[int]:
    """
    解析 ID 引用
    
    可以是：
    - 临时 ID 字符串 (如 "s1", "t1")
    - 数据库真实 ID (整数)
    - None
    """
    if id_ref is None:
        return None
    
    if isinstance(id_ref, int):
        return id_ref
    
    if isinstance(id_ref, str):
        # 尝试作为临时 ID 从映射表查找
        if id_ref in id_map:
            return id_map[id_ref]
        # 尝试转换为整数
        try:
            return int(id_ref)
        except ValueError:
            pass
    
    return None


def _get_entity_type_from_id(id_ref: Any, id_map: Dict[str, int]) -> Optional[str]:
    """根据 ID 引用推断实体类型"""
    if isinstance(id_ref, str):
        if id_ref.startswith('s'):
            return 'S'
        elif id_ref.startswith('t'):
            return 'T'
        elif id_ref.startswith('o'):
            return 'O'
        elif id_ref.startswith('c'):
            return 'C'
    return None


def _create_storyboard_entry(user_id: str, entity_type: str, entity_id: int, entity: Dict[str, Any]) -> Optional[int]:
    """
    创建 Storyboard 条目
    
    格式：[TYPE:ID PARENT:PID] Title | Summary
    """
    type_map = {'S': 1, 'T': 2, 'O': 3, 'C': 4}
    story_type = type_map.get(entity_type, 0)
    
    # 格式化内容
    title = entity.get('title') or entity.get('name', '')
    summary = entity.get('summary', '')
    
    content = f"[{entity_type}:{entity_id}] {title}"
    if summary:
        content += f" | {summary}"
    
    return insert_storyboard(user_id, story_type, entity_id, content)


# ============================================================================
# 触发 Dir Agent
# ============================================================================

async def _trigger_dir_agent(user_id: str):
    """异步触发 Dir Agent"""
    try:
        # 动态导入避免循环依赖
        from .dir_service import run_dir_agent
        await run_dir_agent(user_id)
    except Exception as e:
        logging.error(f"❌ 触发 Dir Agent 失败: {e}")
