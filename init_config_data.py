#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
系统配置数据初始化脚本
初始化 sys_config 和 base_models 表数据
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from database import get_db_connection
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def init_sys_config():
    """初始化系统配置表数据"""
    
    configs = [
        # Session 相关配置
        ('session_ttl', 'Session 有效时长', '3600', 'number', '单位：秒，默认 1 小时'),
        ('session_word_limit', 'Session 字数上限', '10000', 'number', '单位：字，超过此字数需新建 Session'),
        ('session_expire_buf', 'Session 过期缓冲时间', '300', 'number', '单位：秒，提前 5 分钟判断即将过期'),
        
        # 缓存池配置
        ('cache_pool_limit', '缓存池字数阈值', '500', 'number', '单位：字，达到此字数触发速记员处理'),
        ('max_sb_context', 'Story Board 上下文条数', '50', 'number', '单位：条，速记员读取的 SB 记录数'),
        
        # 访谈员 Agent 配置
        ('intv_asr_model', '访谈员 ASR 模型 ID', '1', 'select', '关联 base_models 表'),
        ('intv_llm_model', '访谈员 LLM 模型 ID', '2', 'select', '关联 base_models 表'),
        ('intv_tts_model', '访谈员 TTS 模型 ID', '3', 'select', '关联 base_models 表'),
        ('intv_voice_type', '访谈员 TTS 音色', 'zh_female_vv_uranus_bigtts', 'text', 'Vivi 2.0 音色标识'),
        ('intv_temp', '访谈员 LLM 随机性', '0.7', 'number', '取值范围 0-1，越大越随机'),
        
        # 速记员 Agent 配置
        ('stn_llm_model', '速记员 LLM 模型 ID', '2', 'select', '关联 base_models 表'),
        ('stn_temp', '速记员 LLM 随机性', '0.3', 'number', '取值范围 0-1，速记员需要更稳定'),
        
        # 导演 Agent 配置
        ('dir_llm_model', '导演 LLM 模型 ID', '2', 'select', '关联 base_models 表'),
        ('dir_temp', '导演 LLM 随机性', '0.5', 'number', '取值范围 0-1'),
        
        # 腾讯云 COS 配置（暂时占位）
        ('cos_region', '腾讯云 COS 区域', 'ap-beijing', 'text', '暂时占位，后续配置'),
    ]
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            for config_key, config_name, config_value, config_type, remark in configs:
                # 使用 ON CONFLICT 实现幂等性
                cursor.execute("""
                    INSERT INTO sys_config (config_key, config_name, config_value, config_type, remark)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (config_key) 
                    DO UPDATE SET 
                        config_name = EXCLUDED.config_name,
                        config_value = EXCLUDED.config_value,
                        config_type = EXCLUDED.config_type,
                        remark = EXCLUDED.remark,
                        updated_time = CURRENT_TIMESTAMP
                """, (config_key, config_name, config_value, config_type, remark))
            
            conn.commit()
            logging.info(f"✅ sys_config 表初始化成功（{len(configs)} 条记录）")

def init_base_models():
    """初始化模型库表数据"""
    
    models = [
        # model_id, model_name_cn, model_name_en, model_type, api_model_id, input_price, output_price, cache_discount, cache_storage_price, cluster_id, remark
        (1, '火山引擎 ASR', 'volcengine_streaming_common', 'ASR', 'volcengine_streaming_common', 0.0032, 0, 0.5, 0, 'volcengine_streaming_common', '语音识别模型，价格：¥0.0032/小时'),
        (2, '豆包 Seed', 'doubao-seed-1-8-251228', 'LLM', 'doubao-seed-1-8-251228', 0.8, 2.0, 0.5, 0.01, 'volcano_llm', '大语言模型，输入：¥0.8/百万Token，输出：¥2.0/百万Token'),
        (3, '火山引擎 TTS Vivi 2.0', 'seed-tts-2.0', 'TTS', 'seed-tts-2.0', 0.024, 0, 0.5, 0, 'volcano_tts', '语音合成模型，价格：¥0.024/万字符'),
    ]
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            for model_data in models:
                model_id, model_name_cn, model_name_en, model_type, api_model_id, input_price, output_price, cache_discount, cache_storage_price, cluster_id, remark = model_data
                
                # 先检查是否存在
                cursor.execute("SELECT model_id FROM base_models WHERE model_id = %s", (model_id,))
                exists = cursor.fetchone()
                
                if exists:
                    # 更新
                    cursor.execute("""
                        UPDATE base_models SET
                            model_name_cn = %s,
                            model_name_en = %s,
                            model_type = %s,
                            api_model_id = %s,
                            input_price = %s,
                            output_price = %s,
                            cache_discount = %s,
                            cache_storage_price = %s,
                            cluster_id = %s,
                            remark = %s
                        WHERE model_id = %s
                    """, (model_name_cn, model_name_en, model_type, api_model_id, input_price, output_price, 
                          cache_discount, cache_storage_price, cluster_id, remark, model_id))
                else:
                    # 插入
                    cursor.execute("""
                        INSERT INTO base_models 
                        (model_id, model_name_cn, model_name_en, model_type, api_model_id, input_price, output_price, 
                         cache_discount, cache_storage_price, cluster_id, remark)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    """, model_data)
            
            conn.commit()
            logging.info(f"✅ base_models 表初始化成功（{len(models)} 条记录）")

def verify_data():
    """验证数据是否初始化成功"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # 验证 sys_config
            cursor.execute("SELECT COUNT(*) FROM sys_config")
            config_count = cursor.fetchone()[0]
            
            # 验证 base_models
            cursor.execute("SELECT COUNT(*) FROM base_models")
            model_count = cursor.fetchone()[0]
            
            print("\n" + "=" * 60)
            print("数据验证结果：")
            print("=" * 60)
            print(f"sys_config 表记录数：{config_count}")
            print(f"base_models 表记录数：{model_count}")
            print("=" * 60)
            
            return config_count >= 15 and model_count >= 3

if __name__ == "__main__":
    print("=" * 60)
    print("开始初始化系统配置数据")
    print("=" * 60)
    
    try:
        init_sys_config()
        init_base_models()
        
        if verify_data():
            print("\n🎉 系统配置数据初始化完成！")
        else:
            print("\n⚠️ 数据验证失败，请检查")
            sys.exit(1)
            
    except Exception as e:
        logging.error(f"初始化失败: {e}")
        sys.exit(1)
