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

def _get_ark_client(model_info: Dict[str, Any]) -> AsyncArk:
    """获取 Ark 异步客户端（支持多模型配置）"""
    api_key = model_info.get('api_key')
    base_url = model_info.get('base_url')
    
    if not api_key:
        raise ValueError(f"模型 {model_info.get('model_name_cn')} 的 API Key 未配置")
    
    if not base_url:
        raise ValueError(f"模型 {model_info.get('model_name_cn')} 的 Base URL 未配置")
    
    return AsyncArk(
        base_url=base_url,
        api_key=api_key
    )


def _get_model_info(model_id: int) -> Dict[str, Any]:
    """从 base_models 表获取模型信息"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT model_id, model_name_cn, endpoint_id, api_key, base_url,
                       input_price, output_price, cache_discount
                FROM base_models
                WHERE model_id = %s
            """, (model_id,))
            row = cursor.fetchone()
            
            if not row:
                raise ValueError(f"Model ID {model_id} 不存在")
            
            return {
                'model_id': row[0],
                'model_name_cn': row[1],
                'endpoint_id': row[2],
                'api_key': row[3],
                'base_url': row[4],
                'input_price': float(row[5]) if row[5] else 0,
                'output_price': float(row[6]) if row[6] else 0,
                'cache_discount': float(row[7]) if row[7] else 0.5,
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
        
        client = _get_ark_client(model_info)
        
        # 构建请求参数（严格按照 PRD）
        params = {
            "model": model_info['endpoint_id'],
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
    previous_response_id: Optional[str] = None,
    expire_at: Optional[int] = None,
    temperature: float = None,
    llm_input_str: Optional[str] = None
) -> Dict[str, Any]:
    """
    Stn Agent LLM 调用（非流式，JSON 输出）- 异步版本
    
    PRD 二.2 参数映射:
    - Caching: Enabled (Session 模式) ✅ v3.8 修改
    - Stream: False
    - JSON 模式: text.format.type = "json_object"
    - Previous Response ID: 有值时传入 ✅ v3.8 修改
    
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
        
        if expire_at is None:
            expire_duration = int(get_config('stn_llm_session_expire_duration', default=3600))
            expire_at = int(time.time()) + expire_duration
        
        client = _get_ark_client(model_info)
        
        # 检查是否启用 Caching
        enable_caching = get_config('enable_llm_caching', default='false').lower() == 'true'
        
        # 构建请求参数
        params = {
            "model": model_info['endpoint_id'],
            "input": input_messages,
            "temperature": temperature,
            "stream": False,
            "store": True,  # ✅ v3.8: 启用 Session 存储
            "expire_at": expire_at,  # ✅ v3.8: 设置过期时间
            "thinking": {"type": "disabled"},
            "text": {"format": {"type": "json_object"}},  # JSON 输出模式
        }
        
        if enable_caching:
            params["extra_body"] = {"caching": {"type": "enabled"}}
            logging.info(f"📝 Stn LLM Caching: ENABLED (Prev ID: {previous_response_id[:20] if previous_response_id else 'None'}...)")
        else:
            logging.info("📝 Stn LLM Caching: DISABLED")
            
        if previous_response_id and enable_caching:
            params["previous_response_id"] = previous_response_id
        
        logging.info(f"📝 Stn LLM 调用: model={model_info['model_name_cn']}, caching={enable_caching}")
        
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
        
        # 提取 usage（包含 cached_tokens）
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
                'cached_tokens': cached_tokens,  # ✅ v3.8: 记录缓存 tokens
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
        
        logging.info(f"✅ Stn LLM 调用成功: {len(content)} 字符, {duration_ms}ms, cached={usage_data.get('cached_tokens', 0) if usage_data else 0}")
        
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
        
        client = _get_ark_client(model_info)
        
        # 构建请求参数
        params = {
            "model": model_info['endpoint_id'],
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
# Wtr Agent LLM 调用 (非流式, JSON 模式, 无 Session Caching)
# ============================================================================

async def call_wtr_llm(
    user_id: str,
    input_messages: List[Dict[str, str]],
    temperature: float = None,
    llm_input_str: Optional[str] = None
) -> Dict[str, Any]:
    """
    Wtr Agent LLM 调用（非流式，JSON 输出，不使用 Session Caching）- 异步版本
    
    写作是一次性任务，不需要 Session 延续，因此：
    - Caching: Disabled
    - Stream: False
    - JSON 模式: text.format.type = "json_object"
    
    Returns:
        dict:
            - success: bool
            - content: str (JSON 字符串)
            - usage: dict
            - error: str (如果失败)
    """
    start_time = time.time()
    
    try:
        # 获取模型信息
        model_id = int(get_config('wtr_llm_model', default=2))
        model_info = _get_model_info(model_id)
        
        if temperature is None:
            temperature = float(get_config('wtr_llm_temp', default=0.7))
        
        client = _get_ark_client(model_info)
        
        # 构建请求参数（不使用 Session Caching）
        params = {
            "model": model_info['endpoint_id'],
            "input": input_messages,
            "temperature": temperature,
            "stream": False,
            "thinking": {"type": "disabled"},
            "text": {"format": {"type": "json_object"}},  # JSON 输出模式
        }
        
        logging.info(f"✍️  Wtr LLM 调用: model={model_info['model_name_cn']}, temp={temperature}")
        
        # 调用 API (Async)
        response = await client.responses.create(**params)
        
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
                'input_tokens': getattr(response.usage, 'input_tokens', 0),
                'output_tokens': getattr(response.usage, 'output_tokens', 0),
            }
        
        # 计算耗时
        duration_ms = int((time.time() - start_time) * 1000)
        
        logging.info(f"✅ Wtr LLM 调用成功: {len(content)} 字符, {duration_ms}ms")
        
        return {
            "success": True,
            "content": content,
            "usage": usage_data,
            "duration_ms": duration_ms,
            "model_id": model_id,
            "model_name_cn": model_info['model_name_cn']
        }
        
    except Exception as e:
        logging.error(f"❌ Wtr LLM 调用失败: {e}")
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


def record_llm_usage(
    user_id: str,
    agent: str,
    llm_input: str,
    llm_output: str,
    input_tokens: int,
    output_tokens: int,
    total_tokens: int,
    model_id: int = None,
    model_name_cn: str = None,
    duration_ms: int = 0,
    related_original_text_id: Optional[int] = None
):
    """
    公共 LLM 调用记录函数（供外部调用）
    
    Args:
        user_id: 用户 ID
        agent: Agent 名称 (Intv/Stn/Dir/Wtr)
        llm_input: LLM 输入内容
        llm_output: LLM 输出内容
        input_tokens: 输入 token 数
        output_tokens: 输出 token 数
        total_tokens: 总 token 数
        model_id: 模型 ID（可选）
        model_name_cn: 模型中文名（可选）
        duration_ms: 调用耗时（毫秒）
        related_original_text_id: 关联的原始文本 ID（可选）
    """
    usage = {
        'total_tokens': total_tokens,
        'prompt_tokens': input_tokens,
        'completion_tokens': output_tokens,
        'cached_tokens': 0
    }
    
    _record_llm_usage(
        user_id=user_id,
        agent=agent,
        model_id=model_id or 0,
        model_name_cn=model_name_cn or 'Unknown',
        usage=usage,
        duration_ms=duration_ms,
        llm_input=llm_input,
        llm_output=llm_output,
        related_original_text_id=related_original_text_id
    )

