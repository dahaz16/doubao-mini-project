# -*- coding: utf-8 -*-
"""
============================================================================
Writing Tables Migration Script (写作功能数据库迁移脚本)
============================================================================

基于《我的故事页需求文档 v0.5.md》，增量迁移数据库：
1. ALTER TABLE topic - 新增 topic_writing_state 字段
2. CREATE TABLE writing_source_cachepool - 写作素材缓存池
3. CREATE TABLE writing_status - 写作状态表
4. CREATE TABLE memoir_chapter - 回忆录章节表
5. CREATE TABLE memoir_article - 回忆录文章表

执行方式：
    python migrate_writing_tables.py
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from database import get_db_connection
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')


def check_existing_tables():
    """检查现有表结构"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            logging.info("📋 检查现有表结构...")
            
            # 检查 topic 表是否已有 topic_writing_state 字段
            cursor.execute("""
                SELECT column_name 
                FROM information_schema.columns 
                WHERE table_name = 'topic' AND column_name = 'topic_writing_state'
            """)
            has_writing_state = cursor.fetchone() is not None
            
            # 检查新表是否已存在
            tables_to_check = [
                'writing_source_cachepool',
                'writing_status',
                'memoir_chapter',
                'memoir_article'
            ]
            
            existing_tables = []
            for table in tables_to_check:
                cursor.execute("""
                    SELECT table_name 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = %s
                """, (table,))
                if cursor.fetchone():
                    existing_tables.append(table)
            
            return has_writing_state, existing_tables


def alter_topic_table():
    """为 topic 表新增 topic_writing_state 字段"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            logging.info("🔧 修改 topic 表...")
            
            cursor.execute("""
                ALTER TABLE topic 
                ADD COLUMN IF NOT EXISTS topic_writing_state SMALLINT DEFAULT 0
            """)
            
            cursor.execute("""
                COMMENT ON COLUMN topic.topic_writing_state IS 
                '写作状态: 0=pending(待写作), 1=writing(写作中), 2=done(已写入回忆录)'
            """)
            
            conn.commit()
            logging.info("  ✓ topic.topic_writing_state 字段已添加")


def create_writing_source_cachepool():
    """创建写作素材缓存池表"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            logging.info("🔨 创建 writing_source_cachepool 表...")
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS writing_source_cachepool (
                    writing_source_id BIGSERIAL PRIMARY KEY,
                    topic_id BIGINT REFERENCES topic(topic_id) ON DELETE CASCADE,
                    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
                    created_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(topic_id)
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_writing_source_user_id 
                ON writing_source_cachepool(user_id)
            """)
            
            cursor.execute("""
                COMMENT ON TABLE writing_source_cachepool IS 
                '写作素材缓存池：存储待写作的 topic_id 引用'
            """)
            
            conn.commit()
            logging.info("  ✓ writing_source_cachepool 表已创建")


def create_writing_status():
    """创建写作状态表"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            logging.info("🔨 创建 writing_status 表...")
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS writing_status (
                    user_id UUID PRIMARY KEY REFERENCES users(user_id) ON DELETE CASCADE,
                    cachepool_words_count INTEGER DEFAULT 0,
                    writing_state SMALLINT DEFAULT 0,
                    updated_time TIMESTAMPTZ DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            cursor.execute("""
                COMMENT ON COLUMN writing_status.writing_state IS 
                '写作状态: 0=pending(未进行写作), 1=writing(正在写作)'
            """)
            
            conn.commit()
            logging.info("  ✓ writing_status 表已创建")


def create_memoir_chapter():
    """创建回忆录章节表"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            logging.info("🔨 创建 memoir_chapter 表...")
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memoir_chapter (
                    chapter_id BIGSERIAL PRIMARY KEY,
                    link_stage_id BIGINT REFERENCES stage(stage_id) ON DELETE CASCADE,
                    chapter_name VARCHAR(255) NOT NULL,
                    chapter_sort_num INTEGER,
                    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
                    created_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(user_id, link_stage_id)
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_memoir_chapter_user_id 
                ON memoir_chapter(user_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_memoir_chapter_sort 
                ON memoir_chapter(user_id, chapter_sort_num)
            """)
            
            cursor.execute("""
                COMMENT ON TABLE memoir_chapter IS 
                '回忆录章节：每个章节对应一个 stage（舞台）'
            """)
            
            conn.commit()
            logging.info("  ✓ memoir_chapter 表已创建")


def create_memoir_article():
    """创建回忆录文章表"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            logging.info("🔨 创建 memoir_article 表...")
            
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS memoir_article (
                    section_id BIGSERIAL PRIMARY KEY,
                    topic_id BIGINT REFERENCES topic(topic_id) ON DELETE CASCADE,
                    user_id UUID REFERENCES users(user_id) ON DELETE CASCADE,
                    chapter_id BIGINT REFERENCES memoir_chapter(chapter_id) ON DELETE CASCADE,
                    section_name VARCHAR(255) NOT NULL,
                    section_content TEXT NOT NULL,
                    section_sort_num INTEGER,
                    created_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(topic_id)
                )
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_memoir_article_user_id 
                ON memoir_article(user_id)
            """)
            
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_memoir_article_chapter 
                ON memoir_article(chapter_id, section_sort_num)
            """)
            
            cursor.execute("""
                COMMENT ON TABLE memoir_article IS 
                '回忆录文章：每篇文章对应一个 topic'
            """)
            
            conn.commit()
            logging.info("  ✓ memoir_article 表已创建")


def verify_migration():
    """验证迁移结果"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            print("\n" + "=" * 60)
            print("📊 迁移结果验证")
            print("=" * 60)
            
            # 验证 topic_writing_state 字段
            cursor.execute("""
                SELECT column_name, data_type, column_default
                FROM information_schema.columns
                WHERE table_name = 'topic' AND column_name = 'topic_writing_state'
            """)
            result = cursor.fetchone()
            if result:
                print(f"✓ topic.topic_writing_state: {result[1]} (默认值: {result[2]})")
            else:
                print("✗ topic.topic_writing_state 字段未找到")
            
            # 验证新表
            new_tables = [
                'writing_source_cachepool',
                'writing_status',
                'memoir_chapter',
                'memoir_article'
            ]
            
            print("\n新增表验证:")
            for table in new_tables:
                cursor.execute("""
                    SELECT COUNT(*) 
                    FROM information_schema.tables 
                    WHERE table_schema = 'public' AND table_name = %s
                """, (table,))
                exists = cursor.fetchone()[0] > 0
                
                if exists:
                    cursor.execute(f"SELECT COUNT(*) FROM {table}")
                    count = cursor.fetchone()[0]
                    print(f"  ✓ {table:30s} (当前记录数: {count})")
                else:
                    print(f"  ✗ {table:30s} 未创建")
            
            print("=" * 60)


def insert_test_data():
    """插入测试数据（可选）"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            logging.info("📝 检查是否需要初始化 writing_status...")
            
            # 为所有现有用户创建 writing_status 记录
            cursor.execute("""
                INSERT INTO writing_status (user_id, cachepool_words_count, writing_state)
                SELECT user_id, 0, 0
                FROM users
                WHERE user_id NOT IN (SELECT user_id FROM writing_status)
            """)
            
            rows_inserted = cursor.rowcount
            conn.commit()
            
            if rows_inserted > 0:
                logging.info(f"  ✓ 为 {rows_inserted} 个用户初始化了 writing_status")
            else:
                logging.info("  ✓ 所有用户已有 writing_status 记录")


if __name__ == "__main__":
    print("=" * 60)
    print("Writing Tables Migration Script")
    print("=" * 60)
    
    try:
        # 1. 检查现有表结构
        has_writing_state, existing_tables = check_existing_tables()
        
        if has_writing_state:
            logging.info("⚠️  topic.topic_writing_state 字段已存在，跳过")
        
        if existing_tables:
            logging.info(f"⚠️  以下表已存在，将跳过创建: {', '.join(existing_tables)}")
        
        print()
        
        # 2. 修改 topic 表
        if not has_writing_state:
            alter_topic_table()
        
        # 3. 创建新表
        if 'writing_source_cachepool' not in existing_tables:
            create_writing_source_cachepool()
        
        if 'writing_status' not in existing_tables:
            create_writing_status()
        
        if 'memoir_chapter' not in existing_tables:
            create_memoir_chapter()
        
        if 'memoir_article' not in existing_tables:
            create_memoir_article()
        
        # 4. 初始化数据
        insert_test_data()
        
        # 5. 验证迁移结果
        verify_migration()
        
        print("\n🎉 数据库迁移完成！")
        
    except Exception as e:
        logging.error(f"❌ 迁移失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
