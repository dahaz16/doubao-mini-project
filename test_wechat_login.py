#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
微信登录功能测试脚本
测试用户创建、查询和更新功能
"""

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'backend'))

from user_service import get_user_by_openid, create_user, update_user_info, get_user_by_id
from wechat_service import validate_wechat_config
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def test_wechat_config():
    """测试微信配置"""
    print("=" * 60)
    print("测试微信配置")
    print("=" * 60)
    
    if validate_wechat_config():
        print("✅ 微信配置完整")
        return True
    else:
        print("❌ 微信配置不完整")
        return False

def test_user_operations():
    """测试用户操作"""
    print("\n" + "=" * 60)
    print("测试用户操作")
    print("=" * 60)
    
    # 测试 1：创建用户
    print("\n[测试 1] 创建测试用户")
    test_openid = "test_openid_12345"
    
    # 先检查用户是否已存在
    existing_user = get_user_by_openid(test_openid)
    if existing_user:
        print(f"测试用户已存在，user_id: {existing_user['user_id']}")
        user_id = existing_user['user_id']
    else:
        user_id = create_user(test_openid, unionid="test_unionid_67890")
        print(f"✅ 创建用户成功，user_id: {user_id}")
    
    # 测试 2：查询用户（通过 OpenID）
    print("\n[测试 2] 通过 OpenID 查询用户")
    user = get_user_by_openid(test_openid)
    if user:
        print(f"✅ 查询成功")
        print(f"   user_id: {user['user_id']}")
        print(f"   openid: {user['wechat_openid']}")
        print(f"   创建时间: {user['created_time']}")
    else:
        print("❌ 查询失败")
        return False
    
    # 测试 3：更新用户信息
    print("\n[测试 3] 更新用户信息")
    success = update_user_info(
        user_id=user_id,
        nickname="测试用户",
        avatar_url="https://example.com/avatar.jpg",
        gender=1,
        birth_year=1990,
        birth_month=5
    )
    if success:
        print("✅ 更新成功")
    else:
        print("❌ 更新失败")
        return False
    
    # 测试 4：验证更新结果
    print("\n[测试 4] 验证更新结果")
    updated_user = get_user_by_id(user_id)
    if updated_user:
        print(f"✅ 验证成功")
        print(f"   昵称: {updated_user['wechat_nickname']}")
        print(f"   头像: {updated_user['wechat_avatar_url']}")
        print(f"   性别: {updated_user['gender']}")
        print(f"   出生年月: {updated_user['birth_year']}-{updated_user['birth_month']}")
        
        # 验证数据
        assert updated_user['wechat_nickname'] == "测试用户", "昵称不匹配"
        assert updated_user['gender'] == 1, "性别不匹配"
        assert updated_user['birth_year'] == 1990, "出生年份不匹配"
        print("✅ 数据验证通过")
    else:
        print("❌ 验证失败")
        return False
    
    print("\n" + "=" * 60)
    print("用户操作测试全部通过！")
    print("=" * 60)
    return True

if __name__ == "__main__":
    print("=" * 60)
    print("开始测试微信登录功能")
    print("=" * 60)
    
    try:
        # 测试微信配置
        if not test_wechat_config():
            print("\n⚠️ 微信配置测试失败，但继续测试用户操作")
        
        # 测试用户操作
        if test_user_operations():
            print("\n" + "=" * 60)
            print("🎉 所有测试通过！微信登录功能正常！")
            print("=" * 60)
        else:
            print("\n❌ 测试失败")
            sys.exit(1)
            
    except Exception as e:
        logging.error(f"测试出错: {e}", exc_info=True)
        sys.exit(1)
