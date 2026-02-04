# -*- coding: utf-8 -*-
"""
管理后台服务模块
提供数据库可视化和配置管理功能
"""

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel
from typing import List, Dict, Any, Optional
from datetime import datetime
from .database import get_db_connection
from .interview_detail_service import get_user_interview_details
import logging

router = APIRouter()

# ============================================================================
# 数据模型
# ============================================================================

class ConfigUpdate(BaseModel):
    config_value: str

class ModelCreate(BaseModel):
    model_name_cn: str
    model_name_en: str
    model_type: str
    api_model_id: str
    input_price: Optional[float] = None
    output_price: Optional[float] = None
    cache_discount: Optional[float] = 0.5
    cache_storage_price: Optional[float] = None
    cluster_id: Optional[str] = None
    remark: Optional[str] = None

class PromptCreate(BaseModel):
    llm_type: int
    prompt_content: str
    remark: Optional[str] = None
    is_active: bool = True


# ============================================================================
# 数据库元数据查询
# ============================================================================

@router.get("/tables")
async def get_all_tables():
    """获取所有表名"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public'
                    ORDER BY table_name
                """)
                tables = [row[0] for row in cursor.fetchall()]
                return {"tables": tables}
    except Exception as e:
        logging.error(f"获取表名失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/tables/{table_name}")
async def get_table_data(
    table_name: str,
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None
):
    """查询单表数据（支持分页和搜索）"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # 获取表结构
                cursor.execute("""
                    SELECT column_name, data_type, is_nullable
                    FROM information_schema.columns
                    WHERE table_schema = 'public' AND table_name = %s
                    ORDER BY ordinal_position
                """, (table_name,))
                columns = [
                    {
                        "name": row[0],
                        "type": row[1],
                        "nullable": row[2] == 'YES'
                    }
                    for row in cursor.fetchall()
                ]
                
                if not columns:
                    raise HTTPException(status_code=404, detail=f"表 {table_name} 不存在")
                
                # 构建查询条件
                where_clause = ""
                params = []
                if search:
                    # 对所有文本类型列进行模糊搜索
                    text_columns = [col['name'] for col in columns if 'char' in col['type'] or col['type'] == 'text']
                    if text_columns:
                        conditions = [f"{col}::text ILIKE %s" for col in text_columns]
                        where_clause = f"WHERE {' OR '.join(conditions)}"
                        params = [f"%{search}%"] * len(text_columns)
                
                # 查询总数
                count_query = f"SELECT COUNT(*) FROM {table_name} {where_clause}"
                cursor.execute(count_query, params)
                total = cursor.fetchone()[0]
                
                # 分页查询数据
                offset = (page - 1) * page_size
                data_query = f"SELECT * FROM {table_name} {where_clause} ORDER BY 1 DESC LIMIT %s OFFSET %s"
                cursor.execute(data_query, params + [page_size, offset])
                
                # 获取列名
                column_names = [desc[0] for desc in cursor.description]
                
                # 转换为字典列表
                rows = cursor.fetchall()
                data = [dict(zip(column_names, row)) for row in rows]
                
                # 处理特殊类型（如 datetime, UUID）
                for row in data:
                    for key, value in row.items():
                        if value is not None and hasattr(value, 'isoformat'):
                            row[key] = value.isoformat()
                        elif value is not None and not isinstance(value, (str, int, float, bool)):
                            row[key] = str(value)
                
                return {
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "data": data,
                    "columns": columns
                }
                
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"查询表数据失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# sys_config 配置管理
# ============================================================================

@router.get("/config/sys")
async def get_sys_configs():
    """获取所有系统配置"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT config_key, config_name, config_value, config_type, remark, updated_time
                    FROM sys_config
                    ORDER BY config_key
                """)
                columns = ['config_key', 'config_name', 'config_value', 'config_type', 'remark', 'updated_time']
                rows = cursor.fetchall()
                data = [dict(zip(columns, row)) for row in rows]
                
                # 处理 datetime
                for item in data:
                    if item['updated_time'] and hasattr(item['updated_time'], 'isoformat'):
                        item['updated_time'] = item['updated_time'].isoformat()
                
                return {"data": data}
    except Exception as e:
        logging.error(f"获取系统配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config/sys/{config_key}")
async def update_sys_config(config_key: str, update: ConfigUpdate):
    """更新系统配置"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE sys_config
                    SET config_value = %s, updated_time = CURRENT_TIMESTAMP
                    WHERE config_key = %s
                    RETURNING config_key
                """, (update.config_value, config_key))
                
                if cursor.rowcount == 0:
                    raise HTTPException(status_code=404, detail=f"配置项 {config_key} 不存在")
                
                conn.commit()
                return {"message": "更新成功", "config_key": config_key}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"更新系统配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# base_models 模型库管理
# ============================================================================

@router.get("/config/models")
async def get_models():
    """获取所有模型"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT model_id, model_name_cn, model_name_en, model_type, api_model_id,
                           input_price, output_price, cache_discount, cache_storage_price,
                           cluster_id, remark
                    FROM base_models
                    ORDER BY model_id
                """)
                columns = ['model_id', 'model_name_cn', 'model_name_en', 'model_type', 'api_model_id',
                          'input_price', 'output_price', 'cache_discount', 'cache_storage_price',
                          'cluster_id', 'remark']
                rows = cursor.fetchall()
                data = [dict(zip(columns, row)) for row in rows]
                
                # 转换 Decimal 为 float
                for item in data:
                    for key in ['input_price', 'output_price', 'cache_discount', 'cache_storage_price']:
                        if item[key] is not None:
                            item[key] = float(item[key])
                
                return {"data": data}
    except Exception as e:
        logging.error(f"获取模型列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config/models")
async def create_model(model: ModelCreate):
    """新增模型"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO base_models (
                        model_name_cn, model_name_en, model_type, api_model_id,
                        input_price, output_price, cache_discount, cache_storage_price,
                        cluster_id, remark
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    RETURNING model_id
                """, (
                    model.model_name_cn, model.model_name_en, model.model_type, model.api_model_id,
                    model.input_price, model.output_price, model.cache_discount, model.cache_storage_price,
                    model.cluster_id, model.remark
                ))
                model_id = cursor.fetchone()[0]
                conn.commit()
                return {"message": "创建成功", "model_id": model_id}
    except Exception as e:
        logging.error(f"创建模型失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/config/models/{model_id}")
async def update_model(model_id: int, model: ModelCreate):
    """更新模型"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    UPDATE base_models
                    SET model_name_cn = %s, model_name_en = %s, model_type = %s, api_model_id = %s,
                        input_price = %s, output_price = %s, cache_discount = %s, cache_storage_price = %s,
                        cluster_id = %s, remark = %s
                    WHERE model_id = %s
                    RETURNING model_id
                """, (
                    model.model_name_cn, model.model_name_en, model.model_type, model.api_model_id,
                    model.input_price, model.output_price, model.cache_discount, model.cache_storage_price,
                    model.cluster_id, model.remark, model_id
                ))
                
                if cursor.rowcount == 0:
                    raise HTTPException(status_code=404, detail=f"模型 {model_id} 不存在")
                
                conn.commit()
                return {"message": "更新成功", "model_id": model_id}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"更新模型失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/config/models/{model_id}")
async def delete_model(model_id: int):
    """删除模型"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("DELETE FROM base_models WHERE model_id = %s RETURNING model_id", (model_id,))
                
                if cursor.rowcount == 0:
                    raise HTTPException(status_code=404, detail=f"模型 {model_id} 不存在")
                
                conn.commit()
                return {"message": "删除成功", "model_id": model_id}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"删除模型失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# prompt_config 提示词管理
# ============================================================================

@router.get("/config/prompts")
async def get_prompts():
    """获取所有提示词配置"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    SELECT prompt_id, llm_type, prompt_content, remark, is_active, created_time
                    FROM prompt_config
                    ORDER BY llm_type, prompt_id DESC
                """)
                columns = ['prompt_id', 'llm_type', 'prompt_content', 'remark', 'is_active', 'created_time']
                rows = cursor.fetchall()
                data = [dict(zip(columns, row)) for row in rows]
                
                # 处理 datetime
                for item in data:
                    if item['created_time'] and hasattr(item['created_time'], 'isoformat'):
                        item['created_time'] = item['created_time'].isoformat()
                
                return {"data": data}
    except Exception as e:
        logging.error(f"获取提示词配置失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config/prompts")
async def create_prompt(prompt: PromptCreate):
    """新增提示词"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # 如果新提示词设置为激活，需要将同类型其他提示词设为非激活
                if prompt.is_active:
                    cursor.execute("""
                        UPDATE prompt_config
                        SET is_active = FALSE
                        WHERE llm_type = %s AND is_active = TRUE
                    """, (prompt.llm_type,))
                
                cursor.execute("""
                    INSERT INTO prompt_config (llm_type, prompt_content, remark, is_active)
                    VALUES (%s, %s, %s, %s)
                    RETURNING prompt_id
                """, (prompt.llm_type, prompt.prompt_content, prompt.remark, prompt.is_active))
                
                prompt_id = cursor.fetchone()[0]
                conn.commit()
                return {"message": "创建成功", "prompt_id": prompt_id}
    except Exception as e:
        logging.error(f"创建提示词失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config/prompts/{prompt_id}/toggle")
async def toggle_prompt_active(prompt_id: int):
    """切换提示词激活状态"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # 获取当前状态和类型
                cursor.execute("""
                    SELECT is_active, llm_type
                    FROM prompt_config
                    WHERE prompt_id = %s
                """, (prompt_id,))
                
                result = cursor.fetchone()
                if not result:
                    raise HTTPException(status_code=404, detail=f"提示词 {prompt_id} 不存在")
                
                current_active, llm_type = result
                new_active = not current_active
                
                # 如果要激活，先将同类型其他提示词设为非激活
                if new_active:
                    cursor.execute("""
                        UPDATE prompt_config
                        SET is_active = FALSE
                        WHERE llm_type = %s AND is_active = TRUE
                    """, (llm_type,))
                
                # 切换当前提示词状态
                cursor.execute("""
                    UPDATE prompt_config
                    SET is_active = %s
                    WHERE prompt_id = %s
                """, (new_active, prompt_id))
                
                conn.commit()
                return {"message": "切换成功", "prompt_id": prompt_id, "is_active": new_active}
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"切换提示词状态失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# ============================================================================
# 用户管理与采访库相关 API
# ============================================================================

@router.get("/users")
async def get_users_list(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    search: Optional[str] = None
):
    """获取用户列表（用于采访详情页）"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # 构建查询条件
                where_clause = ""
                params = []
                if search:
                    where_clause = """
                        WHERE user_name ILIKE %s 
                        OR wechat_openid ILIKE %s 
                        OR user_profile ILIKE %s
                    """
                    search_param = f"%{search}%"
                    params = [search_param, search_param, search_param]
                
                # 查询总数
                count_query = f"SELECT COUNT(*) FROM users {where_clause}"
                cursor.execute(count_query, params)
                total = cursor.fetchone()[0]
                
                # 分页查询数据
                offset = (page - 1) * page_size
                data_query = f"""
                    SELECT 
                        user_id,
                        user_name,
                        redeem_code,
                        wechat_openid,
                        user_profile,
                        created_time
                    FROM users
                    {where_clause}
                    ORDER BY created_time DESC
                    LIMIT %s OFFSET %s
                """
                cursor.execute(data_query, params + [page_size, offset])
                
                # 获取列名
                column_names = [desc[0] for desc in cursor.description]
                
                # 转换为字典列表
                rows = cursor.fetchall()
                data = []
                for row in rows:
                    row_dict = dict(zip(column_names, row))
                    # 处理时间格式
                    if row_dict.get('created_time'):
                        row_dict['created_time'] = row_dict['created_time'].isoformat()
                    data.append(row_dict)
                
                return {
                    "total": total,
                    "page": page,
                    "page_size": page_size,
                    "data": data
                }
    except Exception as e:
        logging.error(f"获取用户列表失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}/interview-details")
async def get_user_interview_details_api(
    user_id: str,
    data_types: Optional[str] = Query(None, description="数据方类型，逗号分隔"),
    start_time: Optional[str] = Query(None, description="开始时间 ISO 8601"),
    end_time: Optional[str] = Query(None, description="结束时间 ISO 8601"),
    page: int = Query(1, ge=1),
    page_size: int = Query(50, ge=1, le=100)
):
    """
    获取用户采访详情列表
    
    支持筛选：
    - data_types: user,intv_output,intv_input,stn_input,stn_output,dir_input,dir_output
    - start_time: 2026-02-01T00:00:00
    - end_time: 2026-02-01T23:59:59
    """
    try:
        # 解析数据类型
        data_type_list = None
        if data_types:
            data_type_list = [dt.strip() for dt in data_types.split(",")]
        
        # 解析时间
        start_dt = None
        end_dt = None
        if start_time:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        if end_time:
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        
        # 调用服务
        result = get_user_interview_details(
            user_id=user_id,
            data_types=data_type_list,
            start_time=start_dt,
            end_time=end_dt,
            page=page,
            page_size=page_size
        )
        
        return {"code": 0, "data": result}
    
    except Exception as e:
        logging.error(f"获取用户采访详情失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/users/{user_id}/debug-logs")
async def get_user_debug_logs_api(
    user_id: str,
    start_time: Optional[str] = Query(None, description="开始时间 ISO 8601"),
    end_time: Optional[str] = Query(None, description="结束时间 ISO 8601")
):
    """
    获取用户的完整 debug 日志
    
    包含:
    - narration_status 完整状态
    - active_prompts 当前激活的 prompts
    - logs 时间线日志(用户输入、AI 输出、LLM 调用记录)
    
    默认查询最近 24 小时的数据
    """
    try:
        from debug_log_service import get_user_debug_logs
        
        # 解析时间
        start_dt = None
        end_dt = None
        if start_time:
            start_dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
        if end_time:
            end_dt = datetime.fromisoformat(end_time.replace('Z', '+00:00'))
        
        # 调用服务
        result = get_user_debug_logs(
            user_id=user_id,
            start_time=start_dt,
            end_time=end_dt
        )
        
        return {"code": 0, "data": result}
    
    except Exception as e:
        logging.error(f"获取用户 debug 日志失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ============================================================================
# 删除用户采访记录 API
# ============================================================================

@router.delete("/users/{user_id}/interview-records")
async def delete_user_interview_records(user_id: str):
    """
    删除用户的所有采访记录
    
    删除范围:
    - interview_original_voice (音频文件,依赖 interview_original_text)
    - interview_original_text (原始对话文本)
    - llm_processed (LLM 调用记录)
    - asr_processed (ASR 调用记录)
    - tts_processed (TTS 调用记录)
    - character (人物表)
    - shot (镜头表)
    - topic (话题表)
    - stage (舞台表)
    - hintboard (导演提示板)
    - storyboard (故事板)
    - narration_status (讲述状态表)
    
    保留:
    - users (用户基础信息)
    
    使用事务确保原子性
    """
    try:
        from .database import get_db_connection
        
        deleted_counts = {
            'interview_original_voice': 0,
            'interview_original_text': 0,
            'llm_processed': 0,
            'asr_processed': 0,
            'tts_processed': 0,
            'character': 0,
            'shot': 0,
            'topic': 0,
            'stage': 0,
            'hintboard': 0,
            'storyboard': 0,
            'narration_status': 0,
        }
        
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                # 按外键依赖顺序删除
                # 重要: llm_processed 有外键引用 interview_original_text,必须先删除
                
                # 1. 删除 llm_processed (有外键引用 interview_original_text)
                cursor.execute("""
                    DELETE FROM llm_processed 
                    WHERE user_id = %s
                """, (user_id,))
                deleted_counts['llm_processed'] = cursor.rowcount
                
                # 2. 删除 asr_processed (通过 original_text_id 关联)
                cursor.execute("""
                    DELETE FROM asr_processed 
                    WHERE original_text_id IN (
                        SELECT interview_original_text_id 
                        FROM interview_original_text 
                        WHERE user_id = %s
                    )
                """, (user_id,))
                deleted_counts['asr_processed'] = cursor.rowcount
                
                # 3. 删除 tts_processed (通过 link_original_text_id 关联)
                cursor.execute("""
                    DELETE FROM tts_processed 
                    WHERE link_original_text_id IN (
                        SELECT interview_original_text_id 
                        FROM interview_original_text 
                        WHERE user_id = %s
                    )
                """, (user_id,))
                deleted_counts['tts_processed'] = cursor.rowcount
                
                # 4. 删除 interview_original_voice (依赖 interview_original_text)
                cursor.execute("""
                    DELETE FROM interview_original_voice 
                    WHERE user_id = %s
                """, (user_id,))
                deleted_counts['interview_original_voice'] = cursor.rowcount
                
                # 5. 删除 interview_original_text (被 llm_processed 引用,必须在 llm_processed 删除后)
                cursor.execute("""
                    DELETE FROM interview_original_text 
                    WHERE user_id = %s
                """, (user_id,))
                deleted_counts['interview_original_text'] = cursor.rowcount
                
                # 6. 删除 character (依赖 shot)
                cursor.execute("""
                    DELETE FROM character 
                    WHERE user_id = %s
                """, (user_id,))
                deleted_counts['character'] = cursor.rowcount
                
                # 7. 删除 shot (依赖 topic)
                cursor.execute("""
                    DELETE FROM shot 
                    WHERE user_id = %s
                """, (user_id,))
                deleted_counts['shot'] = cursor.rowcount
                
                # 8. 删除 topic (依赖 stage)
                cursor.execute("""
                    DELETE FROM topic 
                    WHERE user_id = %s
                """, (user_id,))
                deleted_counts['topic'] = cursor.rowcount
                
                # 9. 删除 stage (独立)
                cursor.execute("""
                    DELETE FROM stage 
                    WHERE user_id = %s
                """, (user_id,))
                deleted_counts['stage'] = cursor.rowcount
                
                # 10. 删除 hintboard (独立)
                cursor.execute("""
                    DELETE FROM hintboard 
                    WHERE user_id = %s
                """, (user_id,))
                deleted_counts['hintboard'] = cursor.rowcount
                
                # 11. 删除 storyboard (独立)
                cursor.execute("""
                    DELETE FROM storyboard 
                    WHERE user_id = %s
                """, (user_id,))
                deleted_counts['storyboard'] = cursor.rowcount
                
                # 12. 删除 narration_status (独立)
                cursor.execute("""
                    DELETE FROM narration_status 
                    WHERE user_id = %s
                """, (user_id,))
                deleted_counts['narration_status'] = cursor.rowcount
                
                # 提交事务
                conn.commit()
        
        total_deleted = sum(deleted_counts.values())
        
        logging.info(f"✅ 删除用户 {user_id[:8]}... 的所有记录成功: {deleted_counts}")
        
        return {
            "code": 0,
            "message": "删除成功",
            "data": {
                "user_id": user_id,
                "deleted_counts": deleted_counts,
                "total_deleted": total_deleted
            }
        }
        
    except Exception as e:
        logging.error(f"❌ 删除用户记录失败: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"删除失败: {str(e)}")


