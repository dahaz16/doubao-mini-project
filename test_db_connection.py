#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
数据库连接测试脚本
测试 Supabase PostgreSQL 连接是否正常
"""

import sys
import os

# 添加 backend 目录到 Python 路径
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from database import test_connection, init_db
import logging

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)

def main():
    print("=" * 60)
    print("开始测试 Supabase PostgreSQL 数据库连接")
    print("=" * 60)
    
    # 测试连接
    print("\n[步骤 1] 测试数据库连接...")
    if test_connection():
        print("✅ 数据库连接成功！")
    else:
        print("❌ 数据库连接失败！请检查配置")
        return False
    
    # 初始化数据库表
    print("\n[步骤 2] 初始化数据库表...")
    try:
        init_db()
        print("✅ 数据库表初始化成功！")
    except Exception as e:
        print(f"❌ 数据库表初始化失败: {e}")
        return False
    
    print("\n" + "=" * 60)
    print("🎉 所有测试通过！数据库配置完成！")
    print("=" * 60)
    return True

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
