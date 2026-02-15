#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 Stn Agent 修复后的 Topic/Shot 存储功能
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from backend.stn_service import _process_parsed_data
from backend.database import get_db_connection

# 测试用户 ID
TEST_USER_ID = 'f5577e07-00b5-4394-836b-cd145a453a69'

# 模拟 Stn LLM 的输出
TEST_DATA = {
    "S": [
        {
            "pt": "n",
            "tid": "s1",
            "id": None,
            "title": "测试舞台",
            "summary": "这是一个测试舞台",
            "content": "测试内容",
            "stage_start_time": "2020年",
            "stage_end_time": "2021年"
        }
    ],
    "T": [
        {
            "pt": "n",
            "tid": "t1",
            "id": None,
            "title": "测试话题",
            "summary": "这是一个测试话题",
            "content": "测试话题内容"
        }
    ],
    "O": [
        {
            "pt": "n",
            "tid": "o1",
            "id": None,
            "title": "测试镜头1",
            "summary": "第一个测试镜头",
            "content": "测试镜头内容1",
            "shot_type": 1
        },
        {
            "pt": "n",
            "tid": "o2",
            "id": None,
            "title": "测试镜头2",
            "summary": "第二个测试镜头",
            "content": "测试镜头内容2",
            "shot_type": 2
        }
    ],
    "C": [],
    "R": [
        {
            "type": "link",
            "src": "t1",
            "tgt": "s1"
        },
        {
            "type": "link",
            "src": "o1",
            "tgt": "t1"
        },
        {
            "type": "link",
            "src": "o2",
            "tgt": "t1"
        }
    ]
}


async def test_stn_storage():
    """测试 Stn 数据存储"""
    print("=" * 60)
    print("开始测试 Stn Agent Topic/Shot 存储功能")
    print("=" * 60)
    
    # 1. 处理数据
    print("\n1. 处理测试数据...")
    try:
        max_story_id = await _process_parsed_data(TEST_USER_ID, TEST_DATA)
        print(f"✅ 数据处理完成，max_story_id = {max_story_id}")
    except Exception as e:
        print(f"❌ 数据处理失败: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    # 2. 验证数据库
    print("\n2. 验证数据库...")
    with get_db_connection() as conn:
        with conn.cursor() as cur:
            # 检查 stage
            cur.execute("""
                SELECT stage_id, stage_title 
                FROM stage 
                WHERE user_id = %s AND stage_title = '测试舞台'
            """, (TEST_USER_ID,))
            stage = cur.fetchone()
            if stage:
                print(f"✅ Stage 存储成功: ID={stage[0]}, Title={stage[1]}")
            else:
                print("❌ Stage 未找到")
            
            # 检查 topic
            cur.execute("""
                SELECT topic_id, topic_title, parent_stage_id
                FROM topic 
                WHERE user_id = %s AND topic_title = '测试话题'
            """, (TEST_USER_ID,))
            topic = cur.fetchone()
            if topic:
                print(f"✅ Topic 存储成功: ID={topic[0]}, Title={topic[1]}, Parent Stage={topic[2]}")
            else:
                print("❌ Topic 未找到")
            
            # 检查 shot
            cur.execute("""
                SELECT shot_id, shot_title, parent_topic_id
                FROM shot 
                WHERE user_id = %s AND shot_title LIKE '测试镜头%'
                ORDER BY shot_id
            """, (TEST_USER_ID,))
            shots = cur.fetchall()
            if shots:
                print(f"✅ Shot 存储成功: 找到 {len(shots)} 个镜头")
                for shot in shots:
                    print(f"   - ID={shot[0]}, Title={shot[1]}, Parent Topic={shot[2]}")
            else:
                print("❌ Shot 未找到")
            
            # 检查 storyboard
            cur.execute("""
                SELECT story_id, story_type, entity_id, story_content
                FROM storyboard 
                WHERE user_id = %s AND story_content LIKE '%测试%'
                ORDER BY story_id DESC
                LIMIT 10
            """, (TEST_USER_ID,))
            storyboards = cur.fetchall()
            if storyboards:
                print(f"\n✅ Storyboard 存储成功: 找到 {len(storyboards)} 条记录")
                for sb in storyboards:
                    print(f"   - ID={sb[0]}, Type={sb[1]}, Entity={sb[2]}, Content={sb[3][:50]}...")
            else:
                print("❌ Storyboard 未找到")
    
    print("\n" + "=" * 60)
    print("测试完成!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    asyncio.run(test_stn_storage())
