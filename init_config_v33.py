# -*- coding: utf-8 -*-
"""
============================================================================
v3.3 配置数据初始化脚本
============================================================================

初始化 sys_config 和 base_models 表的配置数据。
根据《服务端流程文档与数据库结构设计 v3.3》中的配置项清单。
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from database import get_db_connection
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def init_sys_config():
    """初始化系统配置表"""
    
    configs = [
        # ============================================================
        # 缓存池配置
        # ============================================================
        {
            'config_key': 'cache_pool_limit',
            'config_name': '缓存池触发字数',
            'config_value': '200',
            'config_type': 'number',
            'remark': '对话缓存池字数达到此阈值时触发 Stn Agent'
        },
        
        # ============================================================
        # Intv Agent 配置
        # ============================================================
        {
            'config_key': 'intv_llm_model',
            'config_name': '访谈员 LLM 模型',
            'config_value': '1',
            'config_type': 'select',
            'remark': '关联 base_models 表的 model_id'
        },
        {
            'config_key': 'intv_llm_temp',
            'config_name': '访谈员 LLM 温度',
            'config_value': '1.0',
            'config_type': 'number',
            'remark': '建议值 1.0，较高随机性'
        },
        {
            'config_key': 'intv_llm_session_word_limit',
            'config_name': '访谈员 Session 字数上限',
            'config_value': '20000',
            'config_type': 'number',
            'remark': '超过此字数需重建 Session'
        },
        {
            'config_key': 'intv_llm_session_expire_duration',
            'config_name': '访谈员 Session 有效时长',
            'config_value': '3600',
            'config_type': 'number',
            'remark': '单位：秒，默认 1 小时'
        },
        {
            'config_key': 'intv_llm_session_expire_buf',
            'config_name': '访谈员 Session 提前刷新缓冲',
            'config_value': '300',
            'config_type': 'number',
            'remark': '单位：秒，距过期少于此时间需重建'
        },
        
        # ============================================================
        # Stn Agent 配置
        # ============================================================
        {
            'config_key': 'stn_llm_model',
            'config_name': '速记员 LLM 模型',
            'config_value': '2',
            'config_type': 'select',
            'remark': '关联 base_models 表的 model_id'
        },
        {
            'config_key': 'stn_llm_temp',
            'config_name': '速记员 LLM 温度',
            'config_value': '0.1',
            'config_type': 'number',
            'remark': '建议值 0.1，追求准确'
        },
        {
            'config_key': 'stn_llm_session_word_limit',
            'config_name': '速记员 Session 字数上限',
            'config_value': '10000',
            'config_type': 'number',
            'remark': '超过此字数需重建 Session'
        },
        {
            'config_key': 'stn_llm_session_expire_duration',
            'config_name': '速记员 Session 有效时长',
            'config_value': '3600',
            'config_type': 'number',
            'remark': '单位：秒'
        },
        {
            'config_key': 'stn_llm_session_expire_buf',
            'config_name': '速记员 Session 提前刷新缓冲',
            'config_value': '300',
            'config_type': 'number',
            'remark': '单位：秒'
        },
        
        # ============================================================
        # Dir Agent 配置
        # ============================================================
        {
            'config_key': 'dir_llm_model',
            'config_name': '导演 LLM 模型',
            'config_value': '2',
            'config_type': 'select',
            'remark': '关联 base_models 表的 model_id'
        },
        {
            'config_key': 'dir_llm_temp',
            'config_name': '导演 LLM 温度',
            'config_value': '0.7',
            'config_type': 'number',
            'remark': '建议值 0.7'
        },
        {
            'config_key': 'dir_llm_session_word_limit',
            'config_name': '导演 Session 字数上限',
            'config_value': '5000',
            'config_type': 'number',
            'remark': '超过此字数需重建 Session'
        },
        {
            'config_key': 'dir_llm_session_expire_duration',
            'config_name': '导演 Session 有效时长',
            'config_value': '3600',
            'config_type': 'number',
            'remark': '单位：秒'
        },
        {
            'config_key': 'dir_llm_session_expire_buf',
            'config_name': '导演 Session 提前刷新缓冲',
            'config_value': '300',
            'config_type': 'number',
            'remark': '单位：秒'
        },
        
        # ============================================================
        # Storyboard 配置
        # ============================================================
        {
            'config_key': 'max_sb_context',
            'config_name': '故事板最大上下文条数',
            'config_value': '50',
            'config_type': 'number',
            'remark': '获取 SB 完整记录时的最大条数'
        },
        
        # ============================================================
        # ASR/TTS 配置
        # ============================================================
        {
            'config_key': 'intv_asr_model',
            'config_name': 'ASR 模型',
            'config_value': '3',
            'config_type': 'select',
            'remark': '关联 base_models 表的 model_id'
        },
        {
            'config_key': 'intv_tts_model',
            'config_name': 'TTS 模型',
            'config_value': '4',
            'config_type': 'select',
            'remark': '关联 base_models 表的 model_id'
        },
    ]
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            logging.info("📝 初始化 sys_config 表...")
            
            for cfg in configs:
                cursor.execute("""
                    INSERT INTO sys_config (config_key, config_name, config_value, config_type, remark)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (config_key) DO UPDATE SET
                        config_name = EXCLUDED.config_name,
                        config_value = EXCLUDED.config_value,
                        config_type = EXCLUDED.config_type,
                        remark = EXCLUDED.remark,
                        updated_time = CURRENT_TIMESTAMP
                """, (cfg['config_key'], cfg['config_name'], cfg['config_value'], 
                      cfg['config_type'], cfg['remark']))
                logging.info(f"  ✓ {cfg['config_key']}: {cfg['config_value']}")
            
            conn.commit()
            logging.info(f"✅ sys_config 初始化完成，共 {len(configs)} 条配置")


def init_base_models():
    """初始化模型库表"""
    
    models = [
        # ============================================================
        # LLM 模型
        # ============================================================
        {
            'model_name_cn': '豆包-Pro-32k',
            'model_name_en': 'Doubao-Pro-32k',
            'model_type': 'LLM',
            'api_model_id': os.getenv('DOUBAO_PRO_ENDPOINT', 'ep-20250103140325-xxxxx'),
            'input_price': 0.0008,
            'output_price': 0.002,
            'cache_discount': 0.1,
            'cache_storage_price': 0.01,
            'remark': 'Intv Agent 主推理模型'
        },
        {
            'model_name_cn': '豆包-Pro-128k',
            'model_name_en': 'Doubao-Pro-128k',
            'model_type': 'LLM',
            'api_model_id': os.getenv('DOUBAO_PRO_128K_ENDPOINT', 'ep-20250103140325-yyyyy'),
            'input_price': 0.005,
            'output_price': 0.009,
            'cache_discount': 0.1,
            'cache_storage_price': 0.01,
            'remark': 'Stn/Dir Agent 推理模型'
        },
        
        # ============================================================
        # ASR 模型
        # ============================================================
        {
            'model_name_cn': '火山 ASR',
            'model_name_en': 'Volc-ASR',
            'model_type': 'ASR',
            'api_model_id': os.getenv('VOLC_ASR_APPID', 'asr-appid'),
            'input_price': 0.003,
            'output_price': 0,
            'remark': '语音转文字'
        },
        
        # ============================================================
        # TTS 模型
        # ============================================================
        {
            'model_name_cn': '火山 TTS',
            'model_name_en': 'Volc-TTS',
            'model_type': 'TTS',
            'api_model_id': os.getenv('VOLC_TTS_APPID', 'tts-appid'),
            'input_price': 0.003,
            'output_price': 0,
            'cluster_id': os.getenv('VOLC_TTS_CLUSTER', 'volcano_mega'),
            'remark': '文字转语音'
        },
    ]
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            logging.info("📝 初始化 base_models 表...")
            
            # 先清空再插入（保证 model_id 从 1 开始）
            cursor.execute("TRUNCATE TABLE base_models RESTART IDENTITY CASCADE")
            
            for model in models:
                cursor.execute("""
                    INSERT INTO base_models 
                    (model_name_cn, model_name_en, model_type, api_model_id, 
                     input_price, output_price, cache_discount, cache_storage_price, 
                     cluster_id, remark)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    model['model_name_cn'],
                    model['model_name_en'],
                    model['model_type'],
                    model['api_model_id'],
                    model.get('input_price'),
                    model.get('output_price'),
                    model.get('cache_discount'),
                    model.get('cache_storage_price'),
                    model.get('cluster_id'),
                    model.get('remark')
                ))
                logging.info(f"  ✓ [{model['model_type']}] {model['model_name_cn']}")
            
            conn.commit()
            logging.info(f"✅ base_models 初始化完成，共 {len(models)} 条模型")


def verify_config():
    """验证配置数据"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # 检查 sys_config
            cursor.execute("SELECT COUNT(*) FROM sys_config")
            config_count = cursor.fetchone()[0]
            
            # 检查 base_models
            cursor.execute("SELECT model_id, model_name_cn, model_type FROM base_models ORDER BY model_id")
            models = cursor.fetchall()
            
            print("\n" + "=" * 60)
            print(f"sys_config 表：{config_count} 条配置")
            print("=" * 60)
            
            print("\nbase_models 表：")
            print("-" * 40)
            for model_id, name, mtype in models:
                print(f"  ID {model_id}: [{mtype}] {name}")
            
            print("=" * 60)


if __name__ == "__main__":
    print("=" * 60)
    print("v3.3 配置数据初始化脚本")
    print("=" * 60)
    
    try:
        init_sys_config()
        init_base_models()
        verify_config()
        
        print("\n🎉 v3.3 配置数据初始化完成！")
    except Exception as e:
        logging.error(f"初始化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
