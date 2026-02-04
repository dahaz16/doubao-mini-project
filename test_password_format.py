#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试不同的密码格式
"""

import urllib.parse

# 原始密码
raw_password = "rta%3FkR4QCb3$*"

print("=" * 60)
print("密码格式测试")
print("=" * 60)

print(f"\n1. 原始密码（从 Supabase 复制的）:")
print(f"   {raw_password}")

print(f"\n2. URL 解码后的密码:")
decoded = urllib.parse.unquote(raw_password)
print(f"   {decoded}")

print(f"\n3. URL 编码后的密码:")
encoded = urllib.parse.quote(decoded, safe='')
print(f"   {encoded}")

print(f"\n4. 推荐在 .env 中使用的格式:")
print(f"   {decoded}")

print("\n" + "=" * 60)
print("结论：在 .env 文件中应该使用 URL 解码后的密码")
print("=" * 60)
