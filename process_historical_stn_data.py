#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动处理 08:49 的 Stn 输出,将 Topic 和 Shot 插入数据库
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.stn_service import _process_parsed_data
from backend.database import get_db_connection
import json

TEST_USER_ID = 'f5577e07-00b5-4394-836b-cd145a453a69'

async def process_historical_data():
    """处理历史 Stn 数据"""
    print("=" * 60)
    print("手动处理 08:49 的 Stn 输出")
    print("=" * 60)
    
    # 1. 获取 08:49 的 Stn 输出
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT output
                FROM llm_processed 
                WHERE agent = 'Stn' 
                  AND user_id = %s
                  AND model_processed_id = 372
            ''', (TEST_USER_ID,))
            output = cur.fetchone()[0]
            data = json.loads(output)
    
    print("\n1. 获取历史数据...")
    mc = data['memory_content']
    print(f"   S: {len(mc['S'])}, T: {len(mc['T'])}, O: {len(mc['O'])}, C: {len(mc['C'])}, R: {len(mc['R'])}")
    
    # 2. 处理数据
    print("\n2. 处理数据...")
    try:
        max_story_id = await _process_parsed_data(TEST_USER_ID, mc)
        print(f"   ✅ 处理完成, max_story_id = {max_story_id}")
    except Exception as e:
        print(f"   ❌ 处理失败: {e}")
        import traceback
        traceback.print_exc()
        return
    
    # 3. 验证结果
    print("\n3. 验证数据库...")
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # 检查 topic
            cur.execute('''
                SELECT topic_id, topic_title, parent_stage_id
                FROM topic 
                WHERE user_id = %s
                ORDER BY created_time DESC
                LIMIT 5
            ''', (TEST_USER_ID,))
            topics = cur.fetchall()
            if topics:
                print(f"   ✅ Topic 表: {len(topics)} 条记录")
                for t in topics:
                    print(f"      - ID={t[0]}, Title={t[1]}, Parent={t[2]}")
            else:
                print("   ❌ Topic 表仍然为空")
            
            # 检查 shot
            cur.execute('''
                SELECT shot_id, shot_title, parent_topic_id
                FROM shot 
                WHERE user_id = %s
                ORDER BY created_time DESC
                LIMIT 5
            ''', (TEST_USER_ID,))
            shots = cur.fetchall()
            if shots:
                print(f"\n   ✅ Shot 表: {len(shots)} 条记录")
                for s in shots:
                    print(f"      - ID={s[0]}, Title={s[1]}, Parent={s[2]}")
            else:
                print("\n   ❌ Shot 表仍然为空")
    
    print("\n" + "=" * 60)
    print("处理完成!")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(process_historical_data())
