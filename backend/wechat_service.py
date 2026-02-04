# -*- coding: utf-8 -*-
"""
微信 API 服务模块
提供微信小程序登录相关的 API 调用
"""

import os
import requests
import logging
from dotenv import load_dotenv

load_dotenv()

# 微信配置
WECHAT_APPID = os.getenv("WECHAT_APPID")
WECHAT_SECRET = os.getenv("WECHAT_SECRET")

# 微信 API 地址
WECHAT_CODE2SESSION_URL = "https://api.weixin.qq.com/sns/jscode2session"


def code2session(code: str) -> dict:
    """
    调用微信 code2Session 接口
    
    Args:
        code: 微信登录凭证
    
    Returns:
        dict: {
            'openid': '用户唯一标识',
            'session_key': '会话密钥',
            'unionid': '用户在开放平台的唯一标识（可选）',
            'errcode': 错误码（如果有错误）,
            'errmsg': 错误信息（如果有错误）
        }
    """
    try:
        params = {
            'appid': WECHAT_APPID,
            'secret': WECHAT_SECRET,
            'js_code': code,
            'grant_type': 'authorization_code'
        }
        
        response = requests.get(WECHAT_CODE2SESSION_URL, params=params, timeout=10)
        result = response.json()
        
        # 检查是否有错误
        if 'errcode' in result and result['errcode'] != 0:
            logging.error(f"微信 code2Session 失败: {result.get('errmsg')}")
            return result
        
        logging.info(f"微信登录成功，OpenID: {result.get('openid')}")
        return result
        
    except Exception as e:
        logging.error(f"调用微信 API 异常: {e}")
        return {
            'errcode': -1,
            'errmsg': f'调用微信 API 异常: {str(e)}'
        }


def validate_wechat_config() -> bool:
    """
    验证微信配置是否完整
    
    Returns:
        bool: 配置是否完整
    """
    if not WECHAT_APPID or not WECHAT_SECRET:
        logging.error("微信配置不完整，请检查 WECHAT_APPID 和 WECHAT_SECRET")
        return False
    return True
