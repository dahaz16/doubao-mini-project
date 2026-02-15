#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手动处理最近 3 次 Stn LLM 调用的数据
"""

import asyncio
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.stn_service import _process_parsed_data
from backend.database import get_db_connection
import json

TEST_USER_ID = 'f5577e07-00b5-4394-836b-cd145a453a69'

async def process_recent_stn_calls():
    """处理最近的 Stn LLM 调用"""
    print("=" * 60)
    print("手动处理最近 3 次 Stn LLM 调用")
    print("=" * 60)
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # 获取最近 3 次 Stn 调用
            cur.execute('''
                SELECT model_processed_id, created_time, output
                FROM llm_processed 
                WHERE agent = 'Stn' 
                  AND user_id = %s
                ORDER BY created_time DESC 
                LIMIT 3
            ''', (TEST_USER_ID,))
            
            calls = cur.fetchall()
    
    for i, (proc_id, created_time, output) in enumerate(calls, 1):
        print(f"\n{'='*60}")
        print(f"处理调用 #{i} (ID: {proc_id}, Time: {created_time})")
        print(f"{'='*60}")
        
        try:
            data = json.loads(output)
            mc = data.get('memory_content', {})
            
            print(f"数据: S={len(mc.get('S', []))}, T={len(mc.get('T', []))}, O={len(mc.get('O', []))}, C={len(mc.get('C', []))}, R={len(mc.get('R', []))}")
            
            if mc.get('T'):
                print("Topics:")
                for t in mc['T']:
                    print(f"  - {t.get('title')}")
            
            # 处理数据
            max_story_id = await _process_parsed_data(TEST_USER_ID, mc)
            print(f"✅ 处理完成, max_story_id = {max_story_id}")
            
        except Exception as e:
            print(f"❌ 处理失败: {e}")
            import traceback
            traceback.print_exc()
    
    # 验证结果
    print(f"\n{'='*60}")
    print("验证数据库")
    print(f"{'='*60}")
    
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                SELECT topic_id, topic_title, parent_stage_id, created_time
                FROM topic
                WHERE user_id = %s
                ORDER BY created_time DESC
            ''', (TEST_USER_ID,))
            
            topics = cur.fetchall()
            if topics:
                print(f"\n✅ Topic 表: {len(topics)} 条记录")
                for t in topics:
                    print(f"   - ID={t[0]}, Title={t[1]}, Parent={t[2]}, Created={t[3]}")
            else:
                print("\n❌ Topic 表仍然为空")
    
    print(f"\n{'='*60}")
    print("处理完成!")
    print(f"{'='*60}")

if __name__ == "__main__":
    asyncio.run(process_recent_stn_calls())
