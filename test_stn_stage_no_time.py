#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 Stage 入库时 start_time 和 end_time 为 NULL
"""

import sys
sys.path.insert(0, '/Users/wangyituo/Documents/拓的文稿/项目/回忆录项目/回忆录代码项目/doubao-mini-project')

from backend.stn_service import _process_stage
from backend.database import get_db_connection
import uuid

def test_stage_no_time():
    # 模拟 LLM 输出的 Stage 数据（不包含时间）
    stage_data = {
        'pt': 'n',
        'tid': 's1',
        'title': '测试阶段_v3.0',
        'summary': '这是一个测试阶段',
        'content': '详细内容描述，用于验证 v3.0 改造'
    }
    
    # 测试用户 ID - 使用数据库中的真实用户
    test_user_id = 'f5577e07-00b5-4394-836b-cd145a453a69'
    id_map = {}
    
    print(f"开始测试 Stage 入库...")
    print(f"测试用户 ID: {test_user_id}")
    
    # 调用处理函数
    stage_id = _process_stage(test_user_id, stage_data, id_map)
    
    # 验证入库成功
    assert stage_id is not None, "Stage 应该成功入库"
    print(f"✅ Stage 入库成功, ID: {stage_id}")
    
    # 查询数据库验证时间字段
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT stage_start_time, stage_end_time, stage_title FROM stage
                WHERE stage_id = %s
            """, (stage_id,))
            result = cursor.fetchone()
            
            assert result is not None, "应该能查询到 Stage 记录"
            assert result[0] is None, f"stage_start_time 应该为 NULL，实际为: {result[0]}"
            assert result[1] is None, f"stage_end_time 应该为 NULL，实际为: {result[1]}"
            
            print(f"✅ 验证通过:")
            print(f"   - stage_start_time: NULL (正确)")
            print(f"   - stage_end_time: NULL (正确)")
            print(f"   - stage_title: {result[2]}")
    
    print("\n✅ 测试通过: Stage 的 start_time 和 end_time 为 NULL")

if __name__ == '__main__':
    test_stage_no_time()
