#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 get_active_prompt 功能
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from config_manager import get_active_prompt

def test_prompt_loading():
    """测试 prompt 加载功能"""
    print("=" * 60)
    print("测试 Prompt 动态读取功能")
    print("=" * 60)
    
    llm_types = {
        0: "Intv",
        1: "Stn",
        2: "Dir"
    }
    
    for llm_type, name in llm_types.items():
        prompt = get_active_prompt(llm_type)
        if prompt:
            print(f"\n✅ [{name}] Prompt 读取成功 (长度: {len(prompt)} 字符)")
            print(f"   前 80 字符: {prompt[:80]}...")
        else:
            print(f"\n❌ [{name}] Prompt 读取失败")
    
    print("\n" + "=" * 60)

if __name__ == "__main__":
    test_prompt_loading()
