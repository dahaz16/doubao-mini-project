# -*- coding: utf-8 -*-
"""
============================================================================
Writing Config Initialization Script (写作功能配置初始化脚本)
============================================================================

为 Wtr Agent 初始化配置项和 Prompt：
1. sys_config 表新增 4 个配置项
2. prompt_config 表新增 llm_type==3 的 Wtr Prompt

执行方式：
    python init_writing_config.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from database import get_db_connection
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def insert_sys_config():
    """插入 Wtr Agent 相关的系统配置"""
    configs = [
        {
            'config_key': 'wtr_cache_pool_limit',
            'config_name': '写作缓存池触发字数',
            'config_value': '500',
            'config_type': 'number',
            'remark': '缓存池字数达到此值后允许触发写作'
        },
        {
            'config_key': 'wtr_reference_words_limit',
            'config_name': '前情提要最大字数',
            'config_value': '3000',
            'config_type': 'number',
            'remark': '参考文章（reference_article）的最大字数限制'
        },
        {
            'config_key': 'wtr_llm_model',
            'config_name': '写作 LLM 模型',
            'config_value': '2',
            'config_type': 'select',
            'remark': '指向 base_models 表中的模型 ID'
        },
        {
            'config_key': 'wtr_llm_temp',
            'config_name': '写作 LLM Temperature',
            'config_value': '0.7',
            'config_type': 'number',
            'remark': '写作需要一定创造性，建议 0.7-0.9'
        }
    ]
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            logging.info("📝 插入 Wtr Agent 系统配置...")
            
            for config in configs:
                # 检查是否已存在
                cursor.execute("""
                    SELECT config_key FROM sys_config WHERE config_key = %s
                """, (config['config_key'],))
                
                if cursor.fetchone():
                    logging.info(f"  ⚠️  {config['config_key']} 已存在，跳过")
                    continue
                
                cursor.execute("""
                    INSERT INTO sys_config 
                    (config_key, config_name, config_value, config_type, remark, updated_time)
                    VALUES (%s, %s, %s, %s, %s, CURRENT_TIMESTAMP)
                """, (
                    config['config_key'],
                    config['config_name'],
                    config['config_value'],
                    config['config_type'],
                    config['remark']
                ))
                
                logging.info(f"  ✓ {config['config_key']} = {config['config_value']}")
            
            conn.commit()
            logging.info("✅ 系统配置插入完成")


def check_prompt_config_table():
    """检查 prompt_config 表是否存在"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' AND table_name = 'prompt_config'
            """)
            return cursor.fetchone() is not None


def create_prompt_config_table():
    """创建 prompt_config 表（如果不存在）"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            logging.info("🔨 创建 prompt_config 表...")
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS prompt_config (
                    prompt_id BIGSERIAL PRIMARY KEY,
                    llm_type SMALLINT NOT NULL,
                    prompt_content TEXT,
                    remark VARCHAR(255),
                    is_active BOOLEAN DEFAULT TRUE,
                    created_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_prompt_config_llm_type 
                ON prompt_config(llm_type, is_active)
            """)
            
            cursor.execute("""
                COMMENT ON COLUMN prompt_config.llm_type IS 
                'LLM 类型: 0=Intv, 1=Stn, 2=Dir, 3=Wtr'
            """)
            
            conn.commit()
            logging.info("  ✓ prompt_config 表已创建")


def insert_wtr_prompt():
    """插入 Wtr Agent 的 System Prompt"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            logging.info("📝 插入 Wtr Agent Prompt...")
            
            # 检查是否已有 llm_type==3 的 prompt
            cursor.execute("""
                SELECT prompt_id FROM prompt_config WHERE llm_type = 3
            """)
            
            if cursor.fetchone():
                logging.info("  ⚠️  Wtr Prompt (llm_type=3) 已存在，跳过")
                return
            
            wtr_prompt = "你是一位专业的回忆录写作者。"
            
            cursor.execute("""
                INSERT INTO prompt_config 
                (llm_type, prompt_content, remark, is_active, created_time)
                VALUES (%s, %s, %s, %s, CURRENT_TIMESTAMP)
            """, (
                3,  # llm_type = 3 (Wtr)
                wtr_prompt,
                'Wtr Agent 初始 Prompt',
                True
            ))
            
            conn.commit()
            logging.info(f"  ✓ Wtr Prompt 已插入: \"{wtr_prompt}\"")


def verify_initialization():
    """验证初始化结果"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            print("\n" + "=" * 60)
            print("📊 配置初始化验证")
            print("=" * 60)
            
            # 验证 sys_config
            print("\nsys_config 表中的 Wtr 配置:")
            cursor.execute("""
                SELECT config_key, config_value, config_type
                FROM sys_config
                WHERE config_key LIKE 'wtr_%'
                ORDER BY config_key
            """)
            
            configs = cursor.fetchall()
            for key, value, ctype in configs:
                print(f"  ✓ {key:30s} = {value:10s} ({ctype})")
            
            if not configs:
                print("  ✗ 未找到 Wtr 相关配置")
            
            # 验证 prompt_config
            print("\nprompt_config 表中的 Wtr Prompt:")
            cursor.execute("""
                SELECT prompt_id, prompt_content, is_active, created_time
                FROM prompt_config
                WHERE llm_type = 3
                ORDER BY prompt_id DESC
            """)
            
            prompts = cursor.fetchall()
            for pid, content, active, created in prompts:
                status = "✓ Active" if active else "✗ Inactive"
                print(f"  [{status}] ID {pid}: \"{content[:50]}...\"")
                print(f"           创建时间: {created}")
            
            if not prompts:
                print("  ✗ 未找到 Wtr Prompt (llm_type=3)")
            
            print("=" * 60)


if __name__ == "__main__":
    print("=" * 60)
    print("Writing Config Initialization Script")
    print("=" * 60)
    
    try:
        # 1. 检查并创建 prompt_config 表
        if not check_prompt_config_table():
            create_prompt_config_table()
        else:
            logging.info("✓ prompt_config 表已存在")
        
        print()
        
        # 2. 插入系统配置
        insert_sys_config()
        
        print()
        
        # 3. 插入 Wtr Prompt
        insert_wtr_prompt()
        
        # 4. 验证初始化结果
        verify_initialization()
        
        print("\n🎉 配置初始化完成！")
        
    except Exception as e:
        logging.error(f"❌ 初始化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
