# -*- coding: utf-8 -*-
"""
============================================================================
v3.9 数据库迁移脚本：base_models 表重构
============================================================================

变更内容：
1. 字段名优化：api_model_id → endpoint_id
2. 新增必填字段：api_key, base_url, api_secret
3. 删除旧数据，重新初始化 5 个模型配置

执行方式：
    python migrate_base_models_v39.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from database import get_db_connection
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def backup_old_data():
    """备份旧数据（可选）"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            logging.info("📦 备份旧数据...")
            
            cursor.execute("SELECT COUNT(*) FROM base_models")
            count = cursor.fetchone()[0]
            
            if count > 0:
                logging.info(f"  当前有 {count} 条模型数据")
                cursor.execute("SELECT model_id, model_name_cn, model_type FROM base_models")
                old_models = cursor.fetchall()
                
                for model_id, name, mtype in old_models:
                    logging.info(f"    - ID {model_id}: [{mtype}] {name}")
            else:
                logging.info("  当前无数据，跳过备份")


def drop_and_recreate_table():
    """删除并重建 base_models 表"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            logging.info("🗑️  删除旧表...")
            cursor.execute("DROP TABLE IF EXISTS base_models CASCADE")
            
            logging.info("🔨 创建新表结构...")
            cursor.execute("""
                CREATE TABLE base_models (
                    model_id BIGSERIAL PRIMARY KEY,
                    model_name_cn VARCHAR(64) NOT NULL,
                    model_name_en VARCHAR(64) NOT NULL,
                    model_type VARCHAR(32) NOT NULL,
                    
                    -- 核心接入字段（必填）
                    endpoint_id VARCHAR(128) NOT NULL,
                    api_key TEXT NOT NULL,
                    base_url TEXT NOT NULL,
                    
                    -- ASR/TTS 专用字段
                    api_secret TEXT,
                    cluster_id VARCHAR(64),
                    
                    -- 价格字段
                    input_price DECIMAL(10,4),
                    output_price DECIMAL(10,4),
                    cache_discount DECIMAL(10,2) DEFAULT 0.5,
                    cache_storage_price DECIMAL(10,4),
                    
                    remark VARCHAR(255),
                    created_time TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # 添加注释
            cursor.execute("""
                COMMENT ON COLUMN base_models.endpoint_id IS 'LLM 用 Endpoint ID (ep-xxx), ASR/TTS 用 App ID';
                COMMENT ON COLUMN base_models.api_key IS 'API 密钥或 Access Key';
                COMMENT ON COLUMN base_models.api_secret IS 'ASR/TTS 专用 Secret Key';
                COMMENT ON COLUMN base_models.base_url IS 'API 基础地址';
            """)
            
            conn.commit()
            logging.info("✅ 新表创建成功")


def init_models():
    """初始化 5 个模型配置"""
    
    models = [
        # ============================================================
        # LLM 模型（3个）
        # ============================================================
        {
            'model_name_cn': '豆包-Pro-32k',
            'model_name_en': 'Doubao-Pro-32k',
            'model_type': 'LLM',
            'endpoint_id': 'ep-20250103140325-xxxxx',
            'api_key': '2e94d489-1cd6-4480-aa76-962a7a7c1a46',
            'base_url': 'https://ark.cn-beijing.volces.com/api/v3',
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
            'endpoint_id': 'ep-20250103140325-yyyyy',
            'api_key': '2e94d489-1cd6-4480-aa76-962a7a7c1a46',
            'base_url': 'https://ark.cn-beijing.volces.com/api/v3',
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
            'endpoint_id': '7689563698',
            'api_key': 'rUdHBaevPF1TRrp4b9ihN6cde5pAWoBt',
            'api_secret': 'BqZOfzsU7obGrdelgWvUTZMS48GCIpAD',
            'base_url': 'wss://openspeech.bytedance.com/api/v3/sauc',
            'cluster_id': 'volcengine_streaming_common',
            'input_price': 0.003,
            'remark': '语音转文字'
        },
        
        # ============================================================
        # TTS 模型
        # ============================================================
        {
            'model_name_cn': '火山 TTS',
            'model_name_en': 'Volc-TTS',
            'model_type': 'TTS',
            'endpoint_id': '7689563698',
            'api_key': 'rUdHBaevPF1TRrp4b9ihN6cde5pAWoBt',
            'api_secret': 'BqZOfzsU7obGrdelgWvUTZMS48GCIpAD',
            'base_url': 'https://openspeech.bytedance.com/api/v1/tts',
            'cluster_id': 'volcano_tts',
            'input_price': 0.003,
            'remark': '文字转语音'
        },
    ]
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            logging.info("📝 初始化模型数据...")
            
            for model in models:
                cursor.execute("""
                    INSERT INTO base_models 
                    (model_name_cn, model_name_en, model_type, endpoint_id, 
                     api_key, api_secret, base_url, cluster_id,
                     input_price, output_price, cache_discount, cache_storage_price, remark)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    model['model_name_cn'],
                    model['model_name_en'],
                    model['model_type'],
                    model['endpoint_id'],
                    model['api_key'],
                    model.get('api_secret'),
                    model['base_url'],
                    model.get('cluster_id'),
                    model.get('input_price'),
                    model.get('output_price'),
                    model.get('cache_discount'),
                    model.get('cache_storage_price'),
                    model.get('remark')
                ))
                logging.info(f"  ✓ [{model['model_type']}] {model['model_name_cn']}")
            
            conn.commit()
            logging.info(f"✅ 模型数据初始化完成，共 {len(models)} 条")


def verify_migration():
    """验证迁移结果"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # 检查表结构
            cursor.execute("""
                SELECT column_name, data_type, is_nullable
                FROM information_schema.columns
                WHERE table_name = 'base_models'
                ORDER BY ordinal_position
            """)
            columns = cursor.fetchall()
            
            print("\n" + "=" * 60)
            print("📊 新表结构验证")
            print("=" * 60)
            
            required_fields = ['endpoint_id', 'api_key', 'base_url', 'api_secret']
            for col_name, col_type, nullable in columns:
                status = "✓" if col_name in required_fields else " "
                null_str = "NULL" if nullable == 'YES' else "NOT NULL"
                print(f"  [{status}] {col_name:20s} {col_type:20s} {null_str}")
            
            # 检查数据
            cursor.execute("SELECT model_id, model_name_cn, model_type, endpoint_id FROM base_models ORDER BY model_id")
            models = cursor.fetchall()
            
            print("\n" + "=" * 60)
            print(f"📦 模型数据验证（共 {len(models)} 条）")
            print("=" * 60)
            
            for model_id, name, mtype, endpoint in models:
                print(f"  ID {model_id}: [{mtype:3s}] {name:15s} → {endpoint}")
            
            print("=" * 60)
            print("\n✅ v3.9 数据库迁移完成！")


if __name__ == "__main__":
    print("=" * 60)
    print("v3.9 数据库迁移脚本：base_models 表重构")
    print("=" * 60)
    
    try:
        # 1. 备份旧数据
        backup_old_data()
        
        # 2. 删除并重建表
        drop_and_recreate_table()
        
        # 3. 初始化模型数据
        init_models()
        
        # 4. 验证迁移结果
        verify_migration()
        
    except Exception as e:
        logging.error(f"❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
