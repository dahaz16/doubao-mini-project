#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证 Agent 链路修复
测试流程:
1. 模拟用户输入多轮对话
2. 检查 chat_cachepool_content 是否正常累积
3. 验证 Stn Agent 是否被触发
4. 验证 Dir Agent 是否被触发
5. 检查数据库中的数据流转
"""

import sys
import time
sys.path.append('.')

from backend.database import get_db_connection

def check_narration_status(user_id: str):
    """检查用户的 narration_status"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    chat_cachepool_content,
                    intv_llm_session_id,
                    stn_llm_session_id,
                    dir_llm_session_id,
                    intv_llm_hint_id
                FROM narration_status
                WHERE user_id = %s
            """, (user_id,))
            
            row = cursor.fetchone()
            if row:
                print(f"\n📊 Narration Status (User: {user_id[:8]}...):")
                print(f"  - 缓存池内容长度: {len(row[0]) if row[0] else 0} 字符")
                print(f"  - 缓存池内容: {row[0][:100] if row[0] else '(空)'}...")
                print(f"  - Intv Session ID: {row[1] or '(未创建)'}")
                print(f"  - Stn Session ID: {row[2] or '(未创建)'}")
                print(f"  - Dir Session ID: {row[3] or '(未创建)'}")
                print(f"  - Hint ID: {row[4] or '(无)'}")
                return row
            else:
                print(f"⚠️ 未找到用户 {user_id} 的 narration_status")
                return None

def check_storyboard(user_id: str):
    """检查 Storyboard 记录"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT story_id, story_type, story_content, stn_processed_status, dir_processed_status
                FROM storyboard
                WHERE user_id = %s
                ORDER BY created_time DESC
                LIMIT 5
            """, (user_id,))
            
            rows = cursor.fetchall()
            if rows:
                print(f"\n📚 Storyboard 记录 (最新 {len(rows)} 条):")
                for row in rows:
                    type_map = {1: 'Stage', 2: 'Topic', 3: 'Shot', 4: 'Character'}
                    story_type = type_map.get(row[1], f'Unknown({row[1]})')
                    print(f"  - ID:{row[0]} | {story_type} | Stn:{row[3]} Dir:{row[4]} | {row[2][:60]}...")
            else:
                print(f"\n📚 Storyboard: 无记录")

def check_hintboard(user_id: str):
    """检查 Hintboard 记录"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT hint_id, hint_content, created_time
                FROM hintboard
                WHERE user_id = %s
                ORDER BY created_time DESC
                LIMIT 3
            """, (user_id,))
            
            rows = cursor.fetchall()
            if rows:
                print(f"\n💡 Hintboard 记录 (最新 {len(rows)} 条):")
                for row in rows:
                    print(f"  - ID:{row[0]} | {row[2]} | {row[1][:80]}...")
            else:
                print(f"\n💡 Hintboard: 无记录")

def check_interview_text(user_id: str):
    """检查最近的对话记录"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT speaker_type, original_text, created_time
                FROM interview_original_text
                WHERE user_id = %s
                ORDER BY created_time DESC
                LIMIT 10
            """, (user_id,))
            
            rows = cursor.fetchall()
            if rows:
                print(f"\n💬 对话记录 (最新 {len(rows)} 条):")
                for row in rows:
                    speaker = "用户" if row[0] == 0 else "AI"
                    print(f"  - {speaker}: {row[1][:60]}... ({row[2]})")
            else:
                print(f"\n💬 对话记录: 无记录")

def get_config_value(key: str):
    """获取配置值"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT config_value
                FROM sys_config
                WHERE config_key = %s
            """, (key,))
            
            row = cursor.fetchone()
            return row[0] if row else None

def main():
    print("=" * 80)
    print("🔍 Agent 链路验证工具")
    print("=" * 80)
    
    # 获取最近活跃的用户
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT user_id, MAX(created_time) as last_time
                FROM interview_original_text
                GROUP BY user_id
                ORDER BY last_time DESC
                LIMIT 1
            """)
            
            row = cursor.fetchone()
            if not row:
                print("⚠️ 数据库中没有对话记录,请先在小程序中进行测试")
                return
            
            user_id = row[0]
    
    print(f"\n🎯 检测到最近活跃用户: {user_id}")
    
    # 获取缓存池阈值
    threshold = get_config_value('cache_pool_limit')
    if threshold is None:
        threshold = 200  # 使用默认值
        print(f"\n⚙️ 缓存池触发阈值: {threshold} 字符 (使用默认值,配置表中未设置)")
    else:
        print(f"\n⚙️ 缓存池触发阈值: {threshold} 字符")
    
    # 检查各项数据
    check_interview_text(user_id)
    status = check_narration_status(user_id)
    check_storyboard(user_id)
    check_hintboard(user_id)
    
    # 分析结果
    print("\n" + "=" * 80)
    print("📋 分析结果:")
    print("=" * 80)
    
    if status:
        cache_len = len(status[0]) if status[0] else 0
        stn_session = status[2]
        dir_session = status[3]
        hint_id = status[4]
        
        print(f"\n✅ 缓存池状态: {cache_len} 字符 (阈值: {threshold})")
        
        if cache_len >= int(threshold):
            print("  ⚠️ 已达到阈值,应该触发 Stn Agent")
        else:
            print(f"  ℹ️ 未达到阈值,还需 {int(threshold) - cache_len} 字符")
        
        if stn_session:
            print(f"\n✅ Stn Agent 已触发 (Session ID: {stn_session})")
        else:
            print("\n❌ Stn Agent 未触发")
        
        if dir_session:
            print(f"✅ Dir Agent 已触发 (Session ID: {dir_session})")
        else:
            print("❌ Dir Agent 未触发")
        
        if hint_id:
            print(f"✅ Hint 已生成 (Hint ID: {hint_id})")
        else:
            print("❌ 尚未生成 Hint")
    
    print("\n" + "=" * 80)
    print("💡 建议:")
    print("=" * 80)
    print("1. 如果缓存池未达到阈值,请继续在小程序中对话")
    print("2. 如果已达到阈值但 Stn Agent 未触发,检查后端日志")
    print("3. 查看日志命令: tail -f backend.log | grep -E '(Stn|Dir|缓存池)'")
    print()

if __name__ == '__main__':
    main()
