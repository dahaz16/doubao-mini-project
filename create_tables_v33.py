# -*- coding: utf-8 -*-
"""
============================================================================
v3.3 数据库表结构创建脚本
============================================================================

根据《服务端流程文档与数据库结构设计 v3.3》创建完整的数据库表结构。
核心变更：
- 新增 narration_status 表（统一管理三个 Agent 的 Session 状态）
- 重建 storyboard 表（使用 stn_processed_status + dir_processed_status）
- 废弃 intv_llm_session、interview_sessions、chat_cachepool 表
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from database import get_db_connection
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def drop_all_tables():
    """删除所有旧表（全新环境重建）"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            logging.info("🗑️  删除所有旧表...")
            
            # 按依赖顺序删除
            tables_to_drop = [
                # 调用记录表
                'tts_processed',
                'asr_processed',
                'llm_processed',
                # 采访溯源表
                'interview_original_voice',
                'interview_original_text',
                # Agent 相关表
                'hintboard',
                'storyboard',
                'story_board',  # 旧表名
                'hint_board',   # 旧表名
                'narration_status',
                # 废弃的 Session 表
                'interview_sessions',
                'intv_llm_session',
                'chat_cachepool',
                # 回忆核心容器
                'character',
                'shot',
                'topic',
                'stage',
                # 基础表
                'users',
                'base_models',
                'sys_config',
            ]
            
            for table in tables_to_drop:
                cursor.execute(f"DROP TABLE IF EXISTS {table} CASCADE")
                logging.info(f"  ✓ 删除表 {table}")
            
            conn.commit()
            logging.info("✅ 所有旧表删除完成")


def create_all_tables():
    """创建所有数据库表（符合 v3.3 PRD）"""
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            
            # ============================================================
            # 1. 系统配置
            # ============================================================
            
            logging.info("创建 sys_config 表...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sys_config (
                    config_key VARCHAR(64) PRIMARY KEY,
                    config_name VARCHAR(64) NOT NULL,
                    config_value TEXT NOT NULL,
                    config_type VARCHAR(32) NOT NULL,
                    remark VARCHAR(255),
                    updated_time TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            logging.info("创建 base_models 表...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS base_models (
                    model_id BIGSERIAL PRIMARY KEY,
                    model_name_cn VARCHAR(64) NOT NULL,
                    model_name_en VARCHAR(64) NOT NULL,
                    model_type VARCHAR(32) NOT NULL,
                    api_model_id VARCHAR(128) NOT NULL,
                    input_price DECIMAL(10,4),
                    output_price DECIMAL(10,4),
                    cache_discount DECIMAL(10,2) DEFAULT 0.5,
                    cache_storage_price DECIMAL(10,4),
                    cluster_id VARCHAR(64),
                    remark VARCHAR(255)
                )
            """)
            
            # ============================================================
            # 2. 用户与权限管理
            # ============================================================
            
            logging.info("创建 users 表...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    wechat_openid VARCHAR(64) UNIQUE NOT NULL,
                    wechat_unionid VARCHAR(64) UNIQUE,
                    wechat_nickname VARCHAR(64),
                    wechat_avatar_url TEXT,
                    wechat_phone_number VARCHAR(20),
                    user_profile TEXT,
                    birth_year INTEGER,
                    birth_month SMALLINT,
                    gender SMALLINT DEFAULT 0,
                    user_type SMALLINT DEFAULT 0,
                    user_name VARCHAR(64) NOT NULL,
                    redeem_code CHAR(4),
                    created_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # ============================================================
            # 3. 回忆核心容器
            # ============================================================
            
            logging.info("创建 stage 表...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS stage (
                    stage_id BIGSERIAL PRIMARY KEY,
                    user_id UUID REFERENCES users(user_id),
                    stage_title VARCHAR(255) NOT NULL,
                    stage_summary TEXT,
                    stage_content TEXT,
                    stage_start_time VARCHAR(64),
                    stage_end_time VARCHAR(64),
                    created_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_stage_user_id ON stage(user_id)")
            
            logging.info("创建 topic 表...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS topic (
                    topic_id BIGSERIAL PRIMARY KEY,
                    user_id UUID REFERENCES users(user_id),
                    parent_stage_id BIGINT REFERENCES stage(stage_id),
                    topic_title VARCHAR(255) NOT NULL,
                    topic_summary TEXT,
                    topic_content TEXT,
                    created_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_topic_user_id ON topic(user_id)")
            
            logging.info("创建 shot 表...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS shot (
                    shot_id BIGSERIAL PRIMARY KEY,
                    user_id UUID REFERENCES users(user_id),
                    parent_topic_id BIGINT REFERENCES topic(topic_id),
                    shot_title VARCHAR(255) NOT NULL,
                    shot_summary TEXT,
                    shot_content TEXT,
                    shot_type SMALLINT,
                    created_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_shot_user_id ON shot(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_shot_title ON shot(shot_title)")
            
            logging.info("创建 character 表...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS character (
                    character_id BIGSERIAL PRIMARY KEY,
                    user_id UUID REFERENCES users(user_id),
                    related_shot_id BIGINT REFERENCES shot(shot_id),
                    name VARCHAR(64) NOT NULL,
                    relation VARCHAR(64),
                    evaluation TEXT,
                    created_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_character_user_id ON character(user_id)")
            
            # ============================================================
            # 4. 系统运行与 Agent 逻辑
            # ============================================================
            
            logging.info("创建 narration_status 表（核心新表）...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS narration_status (
                    narration_status_id BIGSERIAL PRIMARY KEY,
                    user_id UUID UNIQUE REFERENCES users(user_id),
                    
                    -- Intv Agent 状态
                    intv_llm_session_id UUID,
                    intv_llm_session_word_count INTEGER DEFAULT 0,
                    intv_llm_session_expire_at TIMESTAMPTZ,
                    intv_llm_session_previous_response_id VARCHAR(128),
                    intv_llm_previous_content TEXT,
                    intv_llm_hint_id BIGINT,
                    
                    -- Stn Agent 状态
                    stn_llm_session_id UUID,
                    stn_llm_session_word_count INTEGER DEFAULT 0,
                    stn_llm_session_expire_at TIMESTAMPTZ,
                    stn_llm_session_previous_response_id VARCHAR(128),
                    stn_unprocessed_content TEXT,
                    
                    -- Dir Agent 状态
                    dir_llm_session_id UUID,
                    dir_llm_session_word_count INTEGER DEFAULT 0,
                    dir_llm_session_expire_at TIMESTAMPTZ,
                    dir_llm_session_previous_response_id VARCHAR(128),
                    
                    -- 缓存池
                    chat_cachepool_content TEXT
                )
            """)
            
            logging.info("创建 storyboard 表...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS storyboard (
                    story_id BIGSERIAL PRIMARY KEY,
                    user_id UUID REFERENCES users(user_id),
                    story_type SMALLINT,
                    entity_id BIGINT,
                    story_content TEXT,
                    stn_processed_status SMALLINT DEFAULT 0,
                    dir_processed_status SMALLINT DEFAULT 0,
                    created_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_storyboard_user_id ON storyboard(user_id)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_storyboard_stn_status ON storyboard(user_id, stn_processed_status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_storyboard_dir_status ON storyboard(user_id, dir_processed_status)")
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_storyboard_type ON storyboard(story_type)")
            
            logging.info("创建 hintboard 表...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS hintboard (
                    hint_id BIGSERIAL PRIMARY KEY,
                    user_id UUID REFERENCES users(user_id),
                    hint_content TEXT NOT NULL,
                    created_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_hintboard_user_time ON hintboard(user_id, created_time DESC)")
            
            # ============================================================
            # 5. 模型调用记录表
            # ============================================================
            
            logging.info("创建 llm_processed 表...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS llm_processed (
                    model_processed_id BIGSERIAL PRIMARY KEY,
                    user_id UUID REFERENCES users(user_id),
                    agent VARCHAR(64),
                    model_id BIGINT REFERENCES base_models(model_id),
                    model_name_cn VARCHAR(64) NOT NULL,
                    process_duration INTEGER,
                    processed_cost DECIMAL(10,4),
                    total_tokens INTEGER,
                    prompt_tokens INTEGER,
                    completion_tokens INTEGER,
                    cached_tokens INTEGER,
                    created_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            logging.info("创建 asr_processed 表...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS asr_processed (
                    processed_id BIGSERIAL PRIMARY KEY,
                    original_text_id BIGINT,
                    model_id BIGINT REFERENCES base_models(model_id),
                    duration INTEGER,
                    processed_cost DECIMAL(10,6),
                    created_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            logging.info("创建 tts_processed 表...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tts_processed (
                    processed_id BIGSERIAL PRIMARY KEY,
                    link_original_text_id BIGINT,
                    link_original_voice_id BIGINT,
                    model_id BIGINT REFERENCES base_models(model_id),
                    duration INTEGER,
                    processed_cost DECIMAL(10,6),
                    created_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            # ============================================================
            # 6. 采访溯源
            # ============================================================
            
            logging.info("创建 interview_original_text 表...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS interview_original_text (
                    interview_original_text_id BIGSERIAL PRIMARY KEY,
                    user_id UUID REFERENCES users(user_id),
                    speaker_type SMALLINT NOT NULL,
                    has_voice BOOLEAN DEFAULT FALSE,
                    original_text TEXT NOT NULL,
                    created_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_interview_text_user_time ON interview_original_text(user_id, created_time DESC)")
            
            logging.info("创建 interview_original_voice 表...")
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS interview_original_voice (
                    interview_original_voice_id BIGSERIAL PRIMARY KEY,
                    user_id UUID REFERENCES users(user_id),
                    speaker_type SMALLINT NOT NULL,
                    link_original_text_id BIGINT REFERENCES interview_original_text(interview_original_text_id),
                    original_voice_url TEXT NOT NULL,
                    created_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                )
            """)
            cursor.execute("CREATE INDEX IF NOT EXISTS idx_interview_voice_user_id ON interview_original_voice(user_id)")
            
            conn.commit()
            logging.info("✅ 所有表创建成功！")


def verify_tables():
    """验证表是否创建成功"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public' 
                ORDER BY table_name
            """)
            tables = cursor.fetchall()
            
            print("\n" + "=" * 60)
            print(f"数据库中共有 {len(tables)} 张表：")
            print("=" * 60)
            
            expected_tables = [
                'asr_processed',
                'base_models',
                'character',
                'hintboard',
                'interview_original_text',
                'interview_original_voice',
                'llm_processed',
                'narration_status',
                'shot',
                'stage',
                'storyboard',
                'sys_config',
                'topic',
                'tts_processed',
                'users',
            ]
            
            actual_tables = [t[0] for t in tables]
            
            for i, table_name in enumerate(actual_tables, 1):
                status = "✓" if table_name in expected_tables else "?"
                print(f"{i:2d}. [{status}] {table_name}")
            
            # 检查缺失的表
            missing = set(expected_tables) - set(actual_tables)
            if missing:
                print("\n⚠️  缺失的表：")
                for t in missing:
                    print(f"  - {t}")
            else:
                print("\n✅ 所有 v3.3 必需表均已创建！")
            
            print("=" * 60)


if __name__ == "__main__":
    print("=" * 60)
    print("v3.3 数据库表结构重建脚本")
    print("=" * 60)
    
    try:
        # 1. 删除所有旧表
        drop_all_tables()
        
        # 2. 创建新表
        create_all_tables()
        
        # 3. 验证
        verify_tables()
        
        print("\n🎉 v3.3 数据库表结构重建完成！")
    except Exception as e:
        logging.error(f"创建表失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
