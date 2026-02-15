#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""临时脚本:检查 LLM 输出中的 R 数组"""

import sys
import json
sys.path.insert(0, 'backend')

from database import get_db_connection

def check_llm_outputs():
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        print('=== 最近 5 次 Stn LLM 调用的输出 ===\n')
        cur.execute('''
            SELECT model_processed_id, agent, output, created_time 
            FROM llm_processed 
            WHERE agent = 'Stn'
            ORDER BY created_time DESC 
            LIMIT 5;
        ''')
        
        for row in cur.fetchall():
            proc_id, agent, output, created_time = row
            print(f'=== LLM Processed ID: {proc_id}, Time: {created_time} ===')
            
            if output:
                try:
                    # 尝试解析 JSON
                    data = json.loads(output)
                    
                    # 检查是否有 memory_content
                    if 'memory_content' in data:
                        mem_content = data['memory_content']
                        print(f'✅ 发现 memory_content')
                        
                        # 检查各个数组
                        for key in ['S', 'T', 'O', 'C', 'R']:
                            items = mem_content.get(key, [])
                            print(f'  {key}: {len(items)} 条记录')
                            if key == 'R' and items:
                                print(f'  R 数组内容: {json.dumps(items, ensure_ascii=False, indent=2)}')
                    else:
                        # 旧格式
                        print(f'⚠️ 未发现 memory_content,可能是旧格式')
                        for key in ['S', 'T', 'O', 'C', 'R']:
                            items = data.get(key, [])
                            print(f'  {key}: {len(items)} 条记录')
                            if key == 'R' and items:
                                print(f'  R 数组内容: {json.dumps(items, ensure_ascii=False, indent=2)}')
                    
                except json.JSONDecodeError as e:
                    print(f'❌ JSON 解析失败: {e}')
                    print(f'原始输出: {output[:200]}...')
            else:
                print('⚠️ 输出为空')
            
            print('\n' + '='*80 + '\n')
        
        cur.close()

if __name__ == '__main__':
    check_llm_outputs()
