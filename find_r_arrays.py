#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""临时脚本:查找有 R 数组的 LLM 输出"""

import sys
import json
sys.path.insert(0, 'backend')

from database import get_db_connection

def find_r_arrays():
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        print('=== 查找所有有 R 数组的 Stn LLM 调用 ===\n')
        cur.execute('''
            SELECT model_processed_id, agent, output, created_time 
            FROM llm_processed 
            WHERE agent = 'Stn'
            ORDER BY created_time DESC 
            LIMIT 50;
        ''')
        
        found_count = 0
        for row in cur.fetchall():
            proc_id, agent, output, created_time = row
            
            if output:
                try:
                    data = json.loads(output)
                    
                    # 检查 R 数组
                    r_array = None
                    if 'memory_content' in data:
                        r_array = data['memory_content'].get('R', [])
                    else:
                        r_array = data.get('R', [])
                    
                    if r_array and len(r_array) > 0:
                        found_count += 1
                        print(f'=== LLM Processed ID: {proc_id}, Time: {created_time} ===')
                        print(f'R 数组 ({len(r_array)} 条):')
                        print(json.dumps(r_array, ensure_ascii=False, indent=2))
                        print('\n' + '='*80 + '\n')
                        
                except json.JSONDecodeError:
                    pass
        
        print(f'\n总共找到 {found_count} 条有 R 数组的记录')
        
        cur.close()

if __name__ == '__main__':
    find_r_arrays()
