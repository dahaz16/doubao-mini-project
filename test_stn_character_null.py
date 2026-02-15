#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 Character 入库时 related_shot_id 为 NULL
"""

import sys
sys.path.insert(0, '/Users/wangyituo/Documents/拓的文稿/项目/回忆录项目/回忆录代码项目/doubao-mini-project')

from backend.stn_service import _process_character
from backend.database import get_db_connection
import uuid

def test_character_null_shot_id():
    # 模拟 LLM 输出的 Character 数据
    char_data = {
        'pt': 'n',
        'tid': 'c1',
        'name': '测试人物_v3.0',
        'relation': '朋友',
        'evaluation': '很好的朋友'
    }
    
    # 测试用户 ID - 使用数据库中的真实用户
    test_user_id = 'f5577e07-00b5-4394-836b-cd145a453a69'
    id_map = {}
    
    print(f"开始测试 Character 入库...")
    print(f"测试用户 ID: {test_user_id}")
    
    # 调用处理函数
    char_id = _process_character(test_user_id, char_data, id_map)
    
    # 验证入库成功
    assert char_id is not None, "Character 应该成功入库"
    print(f"✅ Character 入库成功, ID: {char_id}")
    
    # 查询数据库验证 related_shot_id
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT related_shot_id, name, relation FROM character
                WHERE character_id = %s
            """, (char_id,))
            result = cursor.fetchone()
            
            assert result is not None, "应该能查询到 Character 记录"
            assert result[0] is None, f"related_shot_id 应该为 NULL，实际为: {result[0]}"
            
            print(f"✅ 验证通过:")
            print(f"   - related_shot_id: NULL (正确)")
            print(f"   - name: {result[1]}")
            print(f"   - relation: {result[2]}")
    
    print("\n✅ 测试通过: Character 的 related_shot_id 为 NULL")

if __name__ == '__main__':
    test_character_null_shot_id()
