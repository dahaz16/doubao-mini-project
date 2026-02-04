#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证 narration_status 表结构
检查是否已有 stn_unprocessed_content 字段
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from database import get_db_connection

def check_narration_status_structure():
    """检查 narration_status 表结构"""
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # 查询表结构
            cursor.execute("""
                SELECT column_name, data_type, is_nullable, column_default
                FROM information_schema.columns
                WHERE table_name = 'narration_status'
                ORDER BY ordinal_position
            """)
            columns = cursor.fetchall()
            
            print("=" * 80)
            print("narration_status 表结构：")
            print("=" * 80)
            
            has_stn_unprocessed = False
            for col_name, data_type, nullable, default in columns:
                print(f"{col_name:40} {data_type:20} {'NULL' if nullable == 'YES' else 'NOT NULL':10}")
                if col_name == 'stn_unprocessed_content':
                    has_stn_unprocessed = True
            
            print("=" * 80)
            
            if has_stn_unprocessed:
                print("✅ stn_unprocessed_content 字段已存在")
            else:
                print("❌ stn_unprocessed_content 字段不存在，需要添加")
            
            return has_stn_unprocessed

if __name__ == "__main__":
    check_narration_status_structure()
