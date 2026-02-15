#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
============================================================================
Storyboard 去重效果监控脚本
============================================================================

快速查看 Storyboard 去重改造的效果
"""

import psycopg2
import os
from dotenv import load_dotenv

load_dotenv()

def main():
    conn = psycopg2.connect(os.getenv('DATABASE_URL'))
    cursor = conn.cursor()
    
    print("\n" + "=" * 70)
    print("  Storyboard 数据监控")
    print("=" * 70)
    
    # 1. 总记录数
    cursor.execute("SELECT COUNT(*) FROM storyboard")
    total = cursor.fetchone()[0]
    print(f"\n📊 总记录数: {total}")
    
    # 2. 重复数据统计
    cursor.execute("""
        SELECT COUNT(DISTINCT entity_id || '-' || story_type) as unique_entities,
               COUNT(*) as total_records
        FROM storyboard
    """)
    unique, total_records = cursor.fetchone()
    duplicate_rate = (total_records - unique) / total_records * 100 if total_records > 0 else 0
    print(f"📊 唯一实体数: {unique}")
    print(f"📊 重复率: {duplicate_rate:.1f}%")
    
    # 3. Top 5 重复最多的实体
    cursor.execute("""
        SELECT entity_id, story_type, COUNT(*) as count
        FROM storyboard
        GROUP BY entity_id, story_type
        HAVING COUNT(*) > 1
        ORDER BY count DESC
        LIMIT 5
    """)
    
    print(f"\n🔝 重复最多的 5 个实体:")
    print(f"{'entity_id':<12} {'story_type':<12} {'重复次数':<12}")
    print("-" * 70)
    
    duplicates = cursor.fetchall()
    if not duplicates:
        print("✅ 没有重复数据")
    else:
        for row in duplicates:
            type_name = {1: 'Stage', 2: 'Topic', 3: 'Shot', 4: 'Character'}.get(row[1], 'Unknown')
            print(f"{row[0]:<12} {type_name:<12} {row[2]:<12}")
    
    # 4. 待处理记录统计
    cursor.execute("""
        SELECT 
            COUNT(*) FILTER (WHERE stn_processed_status = 0) as stn_pending,
            COUNT(*) FILTER (WHERE dir_processed_status = 0) as dir_pending,
            COUNT(*) FILTER (WHERE stn_processed_status = 1 AND dir_processed_status = 1) as fully_processed
        FROM storyboard
    """)
    stn_pending, dir_pending, fully_processed = cursor.fetchone()
    
    print(f"\n📋 处理状态统计:")
    print(f"  待 Stn 处理: {stn_pending}")
    print(f"  待 Dir 处理: {dir_pending}")
    print(f"  已完全处理: {fully_processed}")
    
    # 5. 最近的去重日志（如果有的话）
    print(f"\n💡 提示: 查看后端日志中的 '🗑️  Storyboard 去重' 信息")
    print(f"    tail -f backend.log | grep '🗑️'")
    
    print("\n" + "=" * 70 + "\n")
    
    cursor.close()
    conn.close()

if __name__ == "__main__":
    main()
