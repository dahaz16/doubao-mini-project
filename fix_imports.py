#!/usr/bin/env python3
"""
批量修复 backend 目录下所有 Python 文件的导入语句
将绝对导入改为相对导入
"""
import os
import re

# 需要修复的模块列表
MODULES = [
    'database',
    'ai_service',
    'volc_service',
    'volc_tts_client',
    'wechat_service',
    'user_service',
    'session_service',
    'interview_service',
    'cos_service',
    'audio_service',
    'cachepool_service',
    'stn_database',
    'stn_service',
    'intv_service',
    'admin_service',
    'config_manager',
    'db_logger',
    'llm_api_service',
    'dir_service',
    'narration_service',
    'debug_log_service',
    'interview_detail_service'
]

def fix_imports_in_file(filepath):
    """修复单个文件中的导入语句"""
    with open(filepath, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    modified = False
    
    # 为每个模块创建替换规则
    for module in MODULES:
        # 匹配 "from module import ..." 但不匹配已经是相对导入的
        pattern = rf'^from {module} import'
        replacement = rf'from .{module} import'
        
        # 使用 MULTILINE 标志来匹配每一行的开头
        new_content = re.sub(pattern, replacement, content, flags=re.MULTILINE)
        
        if new_content != content:
            modified = True
            content = new_content
    
    # 如果有修改,写回文件
    if modified:
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        return True
    return False

def main():
    backend_dir = os.path.join(os.path.dirname(__file__), 'backend')
    
    if not os.path.exists(backend_dir):
        print(f"错误: backend 目录不存在: {backend_dir}")
        return
    
    fixed_count = 0
    
    # 遍历 backend 目录下的所有 .py 文件
    for filename in os.listdir(backend_dir):
        if filename.endswith('.py'):
            filepath = os.path.join(backend_dir, filename)
            if fix_imports_in_file(filepath):
                print(f"✅ 修复: {filename}")
                fixed_count += 1
            else:
                print(f"⏭️  跳过: {filename} (无需修改)")
    
    print(f"\n总计修复了 {fixed_count} 个文件")

if __name__ == '__main__':
    main()
