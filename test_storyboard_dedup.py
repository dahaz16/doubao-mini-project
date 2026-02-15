#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
Storyboard 去重逻辑测试脚本
============================================================================

测试 v2024-02-14 的 Storyboard 去重改造（方案 A）

测试内容：
1. 查看当前重复数据情况
2. 模拟 Stn Agent 写入新数据
3. 验证旧记录是否被正确删除
4. 验证待处理记录是否被保留
"""

import psycopg2
import os
from dotenv import load_dotenv
from datetime import datetime

load_dotenv()

def print_separator(title=""):
    """打印分隔线"""
    print("\n" + "=" * 70)
    if title:
        print(f"  {title}")
        print("=" * 70)

def check_duplicates(cursor):
    """检查重复数据情况"""
    print_separator("当前重复数据统计")
    
    cursor.execute("""
        SELECT entity_id, story_type, COUNT(*) as count
        FROM storyboard
        GROUP BY entity_id, story_type
        HAVING COUNT(*) > 1
        ORDER BY count DESC
        LIMIT 10
    """)
    
    print(f"{'entity_id':<12} {'story_type':<12} {'重复次数':<12}")
    print("-" * 70)
    
    duplicates = cursor.fetchall()
    if not duplicates:
        print("✅ 没有重复数据")
    else:
        for row in duplicates:
            print(f"{row[0]:<12} {row[1]:<12} {row[2]:<12}")
    
    return duplicates

def check_entity_records(cursor, entity_id, story_type):
    """查看某个 entity_id 的所有记录"""
    print_separator(f"Entity {entity_id} (Type {story_type}) 的所有记录")
    
    cursor.execute("""
        SELECT story_id, story_content, stn_processed_status, dir_processed_status, created_time
        FROM storyboard
        WHERE entity_id = %s AND story_type = %s
        ORDER BY story_id ASC
    """, (entity_id, story_type))
    
    records = cursor.fetchall()
    
    print(f"{'story_id':<10} {'stn':<5} {'dir':<5} {'created_time':<20} {'content':<30}")
    print("-" * 70)
    
    for row in records:
        story_id, content, stn, dir_status, created = row
        content_short = content[:30] if content else ""
        created_str = created.strftime("%Y-%m-%d %H:%M:%S") if created else ""
        print(f"{story_id:<10} {stn:<5} {dir_status:<5} {created_str:<20} {content_short:<30}")
    
    return records

def simulate_dedup_insert(cursor, user_id, entity_id, story_type, story_content):
    """模拟去重插入逻辑"""
    print_separator(f"模拟插入 Entity {entity_id} (Type {story_type})")
    
    # 1. 删除已处理的旧记录
    cursor.execute("""
        DELETE FROM storyboard
        WHERE user_id = %s 
          AND entity_id = %s 
          AND story_type = %s
          AND stn_processed_status = 1 
          AND dir_processed_status = 1
    """, (user_id, entity_id, story_type))
    
    deleted_count = cursor.rowcount
    print(f"🗑️  删除了 {deleted_count} 条已处理的旧记录")
    
    # 2. 插入新记录
    cursor.execute("""
        INSERT INTO storyboard (user_id, story_type, entity_id, story_content)
        VALUES (%s, %s, %s, %s)
        RETURNING story_id
    """, (user_id, story_type, entity_id, story_content))
    
    new_story_id = cursor.fetchone()[0]
    print(f"✅ 插入新记录: story_id={new_story_id}")
    
    return new_story_id

def main():
    """主测试流程"""
    print_separator("Storyboard 去重逻辑测试")
    print(f"测试时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()
    
    try:
        # 1. 检查当前重复情况
        duplicates = check_duplicates(cursor)
        
        if not duplicates:
            print("\n⚠️  当前没有重复数据，无法测试去重逻辑")
            print("建议：等待 Stn Agent 运行后再测试")
            return
        
        # 2. 选择第一个重复的 entity 进行测试
        test_entity_id, test_story_type, _ = duplicates[0]
        
        # 3. 查看该 entity 的所有记录
        records_before = check_entity_records(cursor, test_entity_id, test_story_type)
        
        # 4. 获取 user_id
        cursor.execute("""
            SELECT user_id FROM storyboard
            WHERE entity_id = %s AND story_type = %s
            LIMIT 1
        """, (test_entity_id, test_story_type))
        user_id = cursor.fetchone()[0]
        
        # 5. 模拟去重插入（不实际提交，只是测试）
        print_separator("⚠️  注意：以下操作不会实际提交到数据库")
        
        # 模拟插入新内容
        new_content = f"[测试] 更新于 {datetime.now().strftime('%H:%M:%S')}"
        simulate_dedup_insert(cursor, user_id, test_entity_id, test_story_type, new_content)
        
        # 6. 查看删除后的记录
        records_after = check_entity_records(cursor, test_entity_id, test_story_type)
        
        # 7. 统计结果
        print_separator("测试结果")
        print(f"删除前记录数: {len(records_before)}")
        print(f"删除后记录数: {len(records_after)}")
        print(f"减少记录数: {len(records_before) - len(records_after)}")
        
        # 8. 检查是否保留了待处理记录
        pending_before = sum(1 for r in records_before if r[2] == 0 or r[3] == 0)
        pending_after = sum(1 for r in records_after if r[2] == 0 or r[3] == 0)
        
        print(f"\n待处理记录（删除前）: {pending_before}")
        print(f"待处理记录（删除后）: {pending_after}")
        
        if pending_before == pending_after:
            print("✅ 待处理记录已正确保留")
        else:
            print("❌ 警告：待处理记录数量变化！")
        
        # 9. 回滚事务（不实际修改数据库）
        conn.rollback()
        print_separator("✅ 测试完成（已回滚，数据库未修改）")
        
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()
