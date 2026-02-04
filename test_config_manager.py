#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
配置读取功能测试脚本
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from config_manager import get_config, get_model_config, get_model_by_config_key
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_config_reading():
    """测试配置读取功能"""
    
    print("=" * 60)
    print("测试配置读取功能")
    print("=" * 60)
    
    # 测试 1：读取数字类型配置
    print("\n[测试 1] 读取数字类型配置")
    session_ttl = get_config('session_ttl')
    print(f"session_ttl = {session_ttl} (类型: {type(session_ttl).__name__})")
    assert isinstance(session_ttl, int), "session_ttl 应该是整数"
    assert session_ttl == 3600, "session_ttl 值应该是 3600"
    print("✅ 通过")
    
    # 测试 2：读取浮点数类型配置
    print("\n[测试 2] 读取浮点数类型配置")
    intv_temp = get_config('intv_temp')
    print(f"intv_temp = {intv_temp} (类型: {type(intv_temp).__name__})")
    assert isinstance(intv_temp, float), "intv_temp 应该是浮点数"
    assert intv_temp == 0.7, "intv_temp 值应该是 0.7"
    print("✅ 通过")
    
    # 测试 3：读取文本类型配置
    print("\n[测试 3] 读取文本类型配置")
    voice_type = get_config('intv_voice_type')
    print(f"intv_voice_type = {voice_type}")
    assert isinstance(voice_type, str), "intv_voice_type 应该是字符串"
    assert voice_type == 'zh_female_vv_uranus_bigtts', "音色值不正确"
    print("✅ 通过")
    
    # 测试 4：读取 select 类型配置（模型 ID）
    print("\n[测试 4] 读取 select 类型配置")
    llm_model_id = get_config('intv_llm_model')
    print(f"intv_llm_model = {llm_model_id} (类型: {type(llm_model_id).__name__})")
    assert isinstance(llm_model_id, int), "intv_llm_model 应该是整数"
    assert llm_model_id == 2, "intv_llm_model 值应该是 2"
    print("✅ 通过")
    
    # 测试 5：读取不存在的配置（使用默认值）
    print("\n[测试 5] 读取不存在的配置")
    non_exist = get_config('non_exist_key', default='default_value')
    print(f"non_exist_key = {non_exist}")
    assert non_exist == 'default_value', "应该返回默认值"
    print("✅ 通过")
    
    print("\n" + "=" * 60)
    print("配置读取测试全部通过！")
    print("=" * 60)

def test_model_config():
    """测试模型配置读取"""
    
    print("\n" + "=" * 60)
    print("测试模型配置读取功能")
    print("=" * 60)
    
    # 测试 1：直接通过 model_id 读取
    print("\n[测试 1] 通过 model_id 读取模型配置")
    model = get_model_config(2)
    print(f"模型名称：{model['model_name_cn']}")
    print(f"API ID：{model['api_model_id']}")
    print(f"输入价格：¥{model['input_price']}/百万Token")
    print(f"输出价格：¥{model['output_price']}/百万Token")
    assert model['model_name_cn'] == '豆包 Seed', "模型名称不正确"
    assert model['api_model_id'] == 'doubao-seed-1-8-251228', "API ID 不正确"
    print("✅ 通过")
    
    # 测试 2：通过配置键读取模型
    print("\n[测试 2] 通过配置键读取模型配置")
    asr_model = get_model_by_config_key('intv_asr_model')
    print(f"ASR 模型：{asr_model['model_name_cn']}")
    print(f"价格：¥{asr_model['input_price']}/小时")
    assert asr_model['model_type'] == 'ASR', "模型类型应该是 ASR"
    print("✅ 通过")
    
    # 测试 3：读取 TTS 模型
    print("\n[测试 3] 读取 TTS 模型配置")
    tts_model = get_model_by_config_key('intv_tts_model')
    print(f"TTS 模型：{tts_model['model_name_cn']}")
    print(f"价格：¥{tts_model['input_price']}/万字符")
    assert tts_model['model_type'] == 'TTS', "模型类型应该是 TTS"
    print("✅ 通过")
    
    print("\n" + "=" * 60)
    print("模型配置读取测试全部通过！")
    print("=" * 60)

if __name__ == "__main__":
    try:
        test_config_reading()
        test_model_config()
        
        print("\n" + "=" * 60)
        print("🎉 所有测试通过！配置管理模块工作正常！")
        print("=" * 60)
        
    except AssertionError as e:
        print(f"\n❌ 测试失败: {e}")
        sys.exit(1)
    except Exception as e:
        logging.error(f"测试出错: {e}")
        sys.exit(1)
