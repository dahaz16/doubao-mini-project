from backend.database import get_db_connection
import json
import re

with get_db_connection() as conn:
    cursor = conn.cursor()
    
    # 查询该用户最近的AI回复
    cursor.execute('''
        SELECT interview_original_text_id, original_text, created_time 
        FROM interview_original_text 
        WHERE user_id = %s 
        AND speaker_type = 1 
        ORDER BY created_time DESC 
        LIMIT 10
    ''', ('32826937-85e6-46cb-812b-e5632fffa5a6',))
    
    results = cursor.fetchall()
    
    # 检测乱码模式
    cot_patterns = [
        r'<\[SILENT_never_used_[a-f0-9]+\]>',
        r'</think_never_used_[a-f0-9]+>',
        r'unittest',
        r'torch',
        r' sys',
        r' ink ',
        r'ffe ',
        r'Ct ',
        r'bef ',
        r'illuminate'
    ]
    
    for row in results:
        text_id, content, created_time = row
        print(f'\n{"="*80}')
        print(f'ID: {text_id}')
        print(f'Time: {created_time}')
        print(f'Length: {len(content)} chars')
        
        # 检查是否包含乱码
        has_cot_leak = False
        for pattern in cot_patterns:
            if re.search(pattern, content):
                has_cot_leak = True
                print(f'⚠️  Found CoT leak pattern: {pattern}')
        
        if has_cot_leak:
            print(f'\n🔴 LEAKED CONTENT:')
            print(content)
        else:
            print(f'\n✅ Clean content (first 200 chars):')
            print(content[:200] + '...' if len(content) > 200 else content)

