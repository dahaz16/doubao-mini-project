#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""临时脚本:查看 Stn Prompt 配置"""

import sys
sys.path.insert(0, 'backend')

from database import get_db_connection

def check_stn_prompt():
    with get_db_connection() as conn:
        cur = conn.cursor()
        
        print('=== Stn Prompt 配置 (llm_type=1) ===\n')
        cur.execute('''
            SELECT prompt_id, is_active, remark, created_time, 
                   LEFT(prompt_content, 500) as content_preview
            FROM prompt_config 
            WHERE llm_type = 1
            ORDER BY created_time DESC 
            LIMIT 5;
        ''')
        
        for row in cur.fetchall():
            prompt_id, is_active, remark, created_time, content = row
            status = "✅ 激活" if is_active else "❌ 未激活"
            print(f'=== Prompt ID: {prompt_id} ({status}) ===')
            print(f'备注: {remark}')
            print(f'创建时间: {created_time}')
            print(f'内容预览 (前500字符):\n{content}...\n')
            print('='*80 + '\n')
        
        # 获取当前激活的完整 Prompt
        print('\n=== 当前激活的 Stn Prompt 完整内容 ===\n')
        cur.execute('''
            SELECT prompt_content
            FROM prompt_config 
            WHERE llm_type = 1 AND is_active = true
            ORDER BY prompt_id DESC 
            LIMIT 1;
        ''')
        
        row = cur.fetchone()
        if row:
            print(row[0])
        else:
            print('⚠️ 未找到激活的 Stn Prompt')
        
        cur.close()

if __name__ == '__main__':
    check_stn_prompt()
