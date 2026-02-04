#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v3.4 Prompt Config 初始化脚本
创建 prompt_config 表并插入初始提示词数据
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from database import get_db_connection
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def create_prompt_config_table():
    """创建 prompt_config 表"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS prompt_config (
                    prompt_id BIGSERIAL PRIMARY KEY,
                    llm_type SMALLINT NOT NULL,
                    prompt_content TEXT,
                    remark VARCHAR(255),
                    is_active BOOLEAN DEFAULT TRUE,
                    created_time TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
                );
            """)
            
            # 创建索引
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_prompt_config_llm_type ON prompt_config(llm_type);
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_prompt_config_active ON prompt_config(is_active);
            """)
            
            conn.commit()
            logging.info("✅ prompt_config 表创建成功")

def init_prompt_data():
    """初始化提示词数据"""
    
    # 访谈员 Prompt (llm_type=0)
    intv_prompt = """# 背景与身份设定
你是"念念"，一个温暖、专业的访谈员，陪伴用户记录他们的人生故事。你的目标是引导用户回忆并分享生命中的美好瞬间、重要人物和难忘经历。

## 对话原则
1. **倾听为主**：鼓励用户自由表达，不打断、不评判
2. **适度追问**：当话题浅尝辄止时，温柔地提出延展性问题
3. **情感共鸣**：理解用户的情绪，给予温暖的回应
4. **自然过渡**：话题转换要自然流畅，避免生硬

## 输入格式说明
你会收到以下格式的输入：
- `ot:` 用户本轮原始输入
- `hc:` 导演提供的提示建议（可选）

请综合这些信息，给出温暖、自然的回应。"""

    # 速记员 Prompt (llm_type=1)
    stn_prompt = """# 任务说明
你是速记员，负责将用户的对话内容整理为结构化的回忆档案。

## 输入格式
- `sb:` Story Board 已有内容
- `uc:` 未成功处理的累计内容（可选）
- `cp:` 本轮缓存池内容

## 输出要求
严格按照 JSON 格式输出，包含 S/T/O/C 实体及关系 R。
使用 pt 字段标记操作类型：n=新建, u=更新, k=保持不变。"""

    # 导演 Prompt (llm_type=2)
    dir_prompt = """# 任务说明
你是导演，负责分析用户的回忆内容，提出后续访谈建议。

## 输入格式
- Story Board 内容（已有的回忆大纲）

## 输出要求
给出 1-3 个开放性问题，引导用户深入回忆细节、情感或关联内容。"""

    prompts = [
        (0, intv_prompt, 'v3.4 访谈员初始提示词'),
        (1, stn_prompt, 'v3.4 速记员初始提示词'),
        (2, dir_prompt, 'v3.4 导演初始提示词'),
    ]
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            for llm_type, content, remark in prompts:
                cursor.execute("""
                    INSERT INTO prompt_config (llm_type, prompt_content, remark, is_active)
                    VALUES (%s, %s, %s, TRUE)
                """, (llm_type, content, remark))
            
            conn.commit()
            logging.info(f"✅ 插入 {len(prompts)} 条提示词配置")

def verify_prompt_config():
    """验证 prompt_config 数据"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("SELECT llm_type, remark, is_active FROM prompt_config ORDER BY llm_type")
            rows = cursor.fetchall()
            
            print("\n" + "=" * 60)
            print("Prompt Config 数据验证：")
            print("=" * 60)
            for llm_type, remark, is_active in rows:
                status = "✅ Active" if is_active else "❌ Inactive"
                llm_name = {0: "Intv", 1: "Stn", 2: "Dir"}.get(llm_type, "Unknown")
                print(f"[{llm_name}] {remark} - {status}")
            print("=" * 60)
            
            return len(rows) >= 3

if __name__ == "__main__":
    print("=" * 60)
    print("开始初始化 Prompt Config")
    print("=" * 60)
    
    try:
        create_prompt_config_table()
        init_prompt_data()
        
        if verify_prompt_config():
            print("\n🎉 Prompt Config 初始化完成！")
        else:
            print("\n⚠️ 数据验证失败")
            sys.exit(1)
    
    except Exception as e:
        logging.error(f"初始化失败: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
