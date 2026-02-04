#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
LLM API Service (Responses API 统一封装)
============================================================================

统一封装 Responses API 调用，支持：
- Session Caching
- Stream / Non-stream
- JSON Output Mode
- Token 消耗记录

根据《服务端流程文档与数据库结构设计 v3.3》中的 LLM API 调用参数规范。
"""

import os
import time
import logging
from typing import Optional, Dict, Any, Generator, List, AsyncGenerator
from datetime import datetime, timezone
from volcenginesdkarkruntime import AsyncArk
from .database import get_db_connection
from .config_manager import get_config

logging.basicConfig(level=logging.INFO)


# ============================================================================
# 客户端初始化
# ============================================================================

def _get_ark_client() -> AsyncArk:
    """获取 Ark 异步客户端"""
    api_key = os.getenv("ARK_API_KEY")
    if not api_key:
        raise ValueError("ARK_API_KEY 环境变量未配置")
    
    return AsyncArk(
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        api_key=api_key
    )


def _get_model_info(model_id: int) -> Dict[str, Any]:
    """从 base_models 表获取模型信息"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT model_id, model_name_cn, api_model_id, input_price, output_price, cache_discount
                FROM base_models
                WHERE model_id = %s
            """, (model_id,))
            row = cursor.fetchone()
            
            if not row:
                raise ValueError(f"Model ID {model_id} 不存在")
            
            return {
                'model_id': row[0],
                'model_name_cn': row[1],
                'api_model_id': row[2],
                'input_price': float(row[3]) if row[3] else 0,
                'output_price': float(row[4]) if row[4] else 0,
                'cache_discount': float(row[5]) if row[5] else 0.5,
            }


# ============================================================================
# Intv Agent LLM 调用 (流式, Session Caching)
# ============================================================================

async def call_intv_llm_stream(
    user_id: str,
    input_messages: List[Dict[str, str]],
    previous_response_id: Optional[str] = None,
    expire_at: Optional[int] = None,
    temperature: float = None,
    llm_input_str: Optional[str] = None,
    related_original_text_id: Optional[int] = None
) -> AsyncGenerator[Dict[str, Any], None]:
    """
    Intv Agent LLM 调用（流式输出）- 异步版本
    
    PRD 二.2 参数映射:
    - Caching: Enabled (Session 模式)
    - Stream: True
    - System Prompt 放在 input 数组第一条
    
    Args:
        user_id: 用户 ID
        input_messages: 消息列表 [{"role": "system/user/assistant", "content": "..."}]
        previous_response_id: 上一轮的 response_id（延续 Session 时传入）
        expire_at: 缓存过期时间（Unix 时间戳）
        temperature: 温度参数，默认从配置获取
    
    Yields:
        dict:
            - {"type": "response_id", "response_id": "xxx"}
            - {"type": "text", "content": "xxx"}
            - {"type": "usage", "usage": {...}}
            - {"type": "done", "response_id": "xxx"}
            - {"type": "error", "message": "xxx"}
    """
    start_time = time.time()
    
    try:
        # 获取模型信息
        model_id = int(get_config('intv_llm_model', default=1))
        model_info = _get_model_info(model_id)
        
        if temperature is None:
            temperature = float(get_config('intv_llm_temp', default=1.0))
        
        if expire_at is None:
            expire_duration = int(get_config('intv_llm_session_expire_duration', default=3600))
            expire_at = int(time.time()) + expire_duration
        
        client = _get_ark_client()
        
        # 构建请求参数（严格按照 PRD）
        params = {
            "model": model_info['api_model_id'],
            "input": input_messages,
            "temperature": temperature,
            "stream": True,
            "store": True,
            "expire_at": expire_at,
            "thinking": {"type": "disabled"},  # Intv 不需要深度思考
        }
        
        # 检查是否启用 Caching
        enable_caching = get_config('enable_llm_caching', default='false').lower() == 'true'
        
        if enable_caching:
            # 开启 Session Caching
            params["extra_body"] = {"caching": {"type": "enabled"}}
        
        if previous_response_id and enable_caching:
            params["previous_response_id"] = previous_response_id
        
        logging.info(f"🎤 Intv LLM 调用: model={model_info['model_name_cn']}, caching={enable_caching}, prev_id={previous_response_id[:20] if previous_response_id else 'None'}...")
        
        # 调用 API (Async)
        stream = await client.responses.create(**params)
        
        response_id = None
        usage_data = None
        full_output = ""  # 收集完整输出
        
        async for event in stream:
            # 1. 提取 Response 元数据 (ID / Usage)
            resp_obj = getattr(event, 'response', None)
            if resp_obj:
                if hasattr(resp_obj, 'id') and not response_id:
                    response_id = resp_obj.id
                    yield {"type": "response_id", "response_id": response_id}
                
                # 提取 Usage
                usage_obj = getattr(resp_obj, 'usage', None)
                if usage_obj:
                    cached_tokens = 0
                    if hasattr(usage_obj, 'input_tokens_details'):
                        details = usage_obj.input_tokens_details
                        cached_tokens = getattr(details, 'cached_tokens', 0) or 0
                    
                    usage_data = {
                        'total_tokens': getattr(usage_obj, 'total_tokens', 0),
                        'prompt_tokens': getattr(usage_obj, 'input_tokens', 0),
                        'completion_tokens': getattr(usage_obj, 'output_tokens', 0),
                        'cached_tokens': cached_tokens,
                    }
            
            # 2. 提取文本增量内容 (Delta)
            delta = getattr(event, 'delta', None)
            if delta:
                full_output += delta  # 累积输出
                yield {"type": "text", "content": delta}
        
        # 计算耗时
        duration_ms = int((time.time() - start_time) * 1000)
        
        # 记录调用
        if usage_data:
            yield {"type": "usage", "usage": usage_data}
            _record_llm_usage(
                user_id=user_id,
                agent="Intv",
                model_id=model_id,
                model_name_cn=model_info['model_name_cn'],
                usage=usage_data,
                duration_ms=duration_ms,
                llm_input=llm_input_str,
                llm_output=full_output,
                related_original_text_id=related_original_text_id
            )
        
        yield {"type": "done", "response_id": response_id}
        
    except Exception as e:
        logging.error(f"❌ Intv LLM 调用失败: {e}")
        yield {"type": "error", "message": str(e)}


# ============================================================================
# Stn Agent LLM 调用 (非流式, JSON 模式, 无 Session)
# ============================================================================

async def call_stn_llm(
    user_id: str,
    input_messages: List[Dict[str, str]],
    temperature: float = None,
    llm_input_str: Optional[str] = None
) -> Dict[str, Any]:
    """
    Stn Agent LLM 调用（非流式，JSON 输出）- 异步版本
    
    PRD 二.2 参数映射:
    - Caching: Disabled
    - Stream: False
    - JSON 模式: text.format.type = "json_object"
    - 无 previous_response_id（单轮任务）
    
    Returns:
        dict:
            - success: bool
            - content: str (JSON 字符串)
            - response_id: str
            - usage: dict
            - error: str (如果失败)
    """
    start_time = time.time()
    
    try:
        # 获取模型信息
        model_id = int(get_config('stn_llm_model', default=2))
        model_info = _get_model_info(model_id)
        
        if temperature is None:
            temperature = float(get_config('stn_llm_temp', default=0.1))
        
        client = _get_ark_client()
        
        # 构建请求参数
        params = {
            "model": model_info['api_model_id'],
            "input": input_messages,
            "temperature": temperature,
            "stream": False,
            "store": False,  # Stn 不需要存储
            "thinking": {"type": "disabled"},
            "text": {"format": {"type": "json_object"}},  # JSON 输出模式
        }
        
        logging.info(f"📝 Stn LLM 调用: model={model_info['model_name_cn']}")
        
        # 调用 API (Async)
        response = await client.responses.create(**params)
        
        # 解析响应
        response_id = response.id if hasattr(response, 'id') else None
        
        # 提取文本内容
        content = ""
        if hasattr(response, 'output') and response.output:
            for output_item in response.output:
                if hasattr(output_item, 'content') and output_item.content:
                    for content_item in output_item.content:
                        if hasattr(content_item, 'text'):
                            content += content_item.text
        
        # 提取 usage
        usage_data = None
        if hasattr(response, 'usage') and response.usage:
            usage_data = {
                'total_tokens': response.usage.total_tokens,
                'prompt_tokens': getattr(response.usage, 'input_tokens', 0),
                'completion_tokens': getattr(response.usage, 'output_tokens', 0),
                'cached_tokens': 0,
            }
        
        # 计算耗时并记录
        duration_ms = int((time.time() - start_time) * 1000)
        
        if usage_data:
            _record_llm_usage(
                user_id=user_id,
                agent="Stn",
                model_id=model_id,
                model_name_cn=model_info['model_name_cn'],
                usage=usage_data,
                duration_ms=duration_ms,
                llm_input=llm_input_str,
                llm_output=content
            )
        
        logging.info(f"✅ Stn LLM 调用成功: {len(content)} 字符, {duration_ms}ms")
        
        return {
            "success": True,
            "content": content,
            "response_id": response_id,
            "usage": usage_data,
        }
        
    except Exception as e:
        logging.error(f"❌ Stn LLM 调用失败: {e}")
        return {
            "success": False,
            "error": str(e),
        }


# ============================================================================
# Dir Agent LLM 调用 (非流式, Session Caching)
# ============================================================================

async def call_dir_llm(
    user_id: str,
    input_messages: List[Dict[str, str]],
    previous_response_id: Optional[str] = None,
    expire_at: Optional[int] = None,
    temperature: float = None,
    llm_input_str: Optional[str] = None
) -> Dict[str, Any]:
    """
    Dir Agent LLM 调用（非流式）- 异步版本
    
    PRD 二.2 参数映射:
    - Caching: Enabled (Session 模式)
    - Stream: False
    
    Returns:
        dict:
            - success: bool
            - content: str
            - response_id: str
            - usage: dict
            - error: str (如果失败)
    """
    start_time = time.time()
    
    try:
        # 获取模型信息
        model_id = int(get_config('dir_llm_model', default=2))
        model_info = _get_model_info(model_id)
        
        if temperature is None:
            temperature = float(get_config('dir_llm_temp', default=0.7))
        
        if expire_at is None:
            expire_duration = int(get_config('dir_llm_session_expire_duration', default=3600))
            expire_at = int(time.time()) + expire_duration
        
        client = _get_ark_client()
        
        # 构建请求参数
        params = {
            "model": model_info['api_model_id'],
            "input": input_messages,
            "temperature": temperature,
            "stream": False,
            "store": True,
            "expire_at": expire_at,
            "thinking": {"type": "disabled"},
        }
        
        # 检查是否启用 Caching
        enable_caching = get_config('enable_llm_caching', default='false').lower() == 'true'
        
        if enable_caching:
            # 开启 Session Caching
            params["extra_body"] = {"caching": {"type": "enabled"}}
        
        if previous_response_id and enable_caching:
            params["previous_response_id"] = previous_response_id
        
        logging.info(f"🎬 Dir LLM 调用: model={model_info['model_name_cn']}, caching={enable_caching}")
        
        # 调用 API (Async)
        response = await client.responses.create(**params)
        
        # 解析响应
        response_id = response.id if hasattr(response, 'id') else None
        
        # 提取文本内容
        content = ""
        if hasattr(response, 'output') and response.output:
            for output_item in response.output:
                if hasattr(output_item, 'content') and output_item.content:
                    for content_item in output_item.content:
                        if hasattr(content_item, 'text'):
                            content += content_item.text
        
        # 提取 usage
        usage_data = None
        if hasattr(response, 'usage') and response.usage:
            cached_tokens = 0
            if hasattr(response.usage, 'input_tokens_details'):
                details = response.usage.input_tokens_details
                if hasattr(details, 'cached_tokens'):
                    cached_tokens = details.cached_tokens or 0
            
            usage_data = {
                'total_tokens': response.usage.total_tokens,
                'prompt_tokens': getattr(response.usage, 'input_tokens', 0),
                'completion_tokens': getattr(response.usage, 'output_tokens', 0),
                'cached_tokens': cached_tokens,
            }
        
        # 计算耗时并记录
        duration_ms = int((time.time() - start_time) * 1000)
        
        if usage_data:
            _record_llm_usage(
                user_id=user_id,
                agent="Dir",
                model_id=model_id,
                model_name_cn=model_info['model_name_cn'],
                usage=usage_data,
                duration_ms=duration_ms,
                llm_input=llm_input_str,
                llm_output=content
            )
        
        logging.info(f"✅ Dir LLM 调用成功: {len(content)} 字符, {duration_ms}ms")
        
        return {
            "success": True,
            "content": content,
            "response_id": response_id,
            "usage": usage_data,
        }
        
    except Exception as e:
        logging.error(f"❌ Dir LLM 调用失败: {e}")
        return {
            "success": False,
            "error": str(e),
        }


# ============================================================================
# LLM 调用记录
# ============================================================================

def _record_llm_usage(
    user_id: str,
    agent: str,
    model_id: int,
    model_name_cn: str,
    usage: Dict[str, int],
    duration_ms: int,
    llm_input: Optional[str] = None,
    llm_output: Optional[str] = None,
    related_original_text_id: Optional[int] = None
):
    """记录 LLM 调用到 llm_processed 表"""
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    INSERT INTO llm_processed 
                    (user_id, agent, model_id, model_name_cn, process_duration,
                     total_tokens, prompt_tokens, completion_tokens, cached_tokens,
                     input, output, related_original_text_id)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    user_id,
                    agent,
                    model_id,
                    model_name_cn,
                    duration_ms,
                    usage.get('total_tokens', 0),
                    usage.get('prompt_tokens', 0),
                    usage.get('completion_tokens', 0),
                    usage.get('cached_tokens', 0),
                    llm_input,
                    llm_output,
                    related_original_text_id,
                ))
                conn.commit()
        
        logging.info(f"📊 记录 LLM 调用: {agent} - {usage.get('total_tokens', 0)} tokens")
        
    except Exception as e:
        logging.error(f"❌ 记录 LLM 调用失败: {e}")
