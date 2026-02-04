# -*- coding: utf-8 -*-
"""
用户服务模块
提供用户数据库操作相关功能
"""

from typing import Optional, Dict, Any
from .database import get_db_connection
import logging
import uuid


def get_user_by_openid(openid: str) -> Optional[Dict[str, Any]]:
    """
    根据微信 OpenID 查询用户
    
    Args:
        openid: 微信 OpenID
    
    Returns:
        用户信息字典，如果不存在返回 None
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT user_id, wechat_openid, wechat_unionid, wechat_nickname, 
                       wechat_avatar_url, wechat_phone_number, user_profile,
                       birth_year, birth_month, gender, user_type, created_time
                FROM users 
                WHERE wechat_openid = %s
            """, (openid,))
            result = cursor.fetchone()
            
            if not result:
                return None
            
            return {
                'user_id': str(result[0]),
                'wechat_openid': result[1],
                'wechat_unionid': result[2],
                'wechat_nickname': result[3],
                'wechat_avatar_url': result[4],
                'wechat_phone_number': result[5],
                'user_profile': result[6],
                'birth_year': result[7],
                'birth_month': result[8],
                'gender': result[9],
                'user_type': result[10],
                'created_time': result[11].isoformat() if result[11] else None
            }


def create_user(openid: str, unionid: Optional[str] = None) -> str:
    """
    创建新用户
    
    Args:
        openid: 微信 OpenID
        unionid: 微信 UnionID（可选）
    
    Returns:
        新用户的 user_id (UUID 字符串)
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            # 生成默认用户名（使用 openid 前8位）
            default_user_name = f"用户_{openid[:8]}"
            
            cursor.execute("""
                INSERT INTO users (wechat_openid, wechat_unionid, user_name)
                VALUES (%s, %s, %s)
                RETURNING user_id
            """, (openid, unionid, default_user_name))
            user_id = cursor.fetchone()[0]
            conn.commit()
            
            logging.info(f"创建新用户成功，user_id: {user_id}, openid: {openid}, user_name: {default_user_name}")
            return str(user_id)


def update_user_info(
    user_id: str,
    nickname: Optional[str] = None,
    avatar_url: Optional[str] = None,
    gender: Optional[int] = None,
    phone_number: Optional[str] = None,
    profile: Optional[str] = None,
    birth_year: Optional[int] = None,
    birth_month: Optional[int] = None
) -> bool:
    """
    更新用户信息
    
    Args:
        user_id: 用户 ID
        nickname: 昵称
        avatar_url: 头像 URL
        gender: 性别（0:未知, 1:男, 2:女）
        phone_number: 手机号
        profile: 个人简介
        birth_year: 出生年份
        birth_month: 出生月份
    
    Returns:
        是否更新成功
    """
    # 构建动态更新语句
    update_fields = []
    params = []
    
    if nickname is not None:
        update_fields.append("wechat_nickname = %s")
        params.append(nickname)
    
    if avatar_url is not None:
        update_fields.append("wechat_avatar_url = %s")
        params.append(avatar_url)
    
    if gender is not None:
        update_fields.append("gender = %s")
        params.append(gender)
    
    if phone_number is not None:
        update_fields.append("wechat_phone_number = %s")
        params.append(phone_number)
    
    if profile is not None:
        update_fields.append("user_profile = %s")
        params.append(profile)
    
    if birth_year is not None:
        update_fields.append("birth_year = %s")
        params.append(birth_year)
    
    if birth_month is not None:
        update_fields.append("birth_month = %s")
        params.append(birth_month)
    
    if not update_fields:
        logging.warning("没有需要更新的字段")
        return False
    
    params.append(user_id)
    
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            sql = f"""
                UPDATE users 
                SET {', '.join(update_fields)}
                WHERE user_id = %s
            """
            cursor.execute(sql, params)
            conn.commit()
            
            logging.info(f"更新用户信息成功，user_id: {user_id}")
            return True


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    """
    根据用户 ID 查询用户
    
    Args:
        user_id: 用户 ID
    
    Returns:
        用户信息字典，如果不存在返回 None
    """
    with get_db_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute("""
                SELECT user_id, wechat_openid, wechat_unionid, wechat_nickname, 
                       wechat_avatar_url, wechat_phone_number, user_profile,
                       birth_year, birth_month, gender, user_type, created_time
                FROM users 
                WHERE user_id = %s
            """, (user_id,))
            result = cursor.fetchone()
            
            if not result:
                return None
            
            return {
                'user_id': str(result[0]),
                'wechat_openid': result[1],
                'wechat_unionid': result[2],
                'wechat_nickname': result[3],
                'wechat_avatar_url': result[4],
                'wechat_phone_number': result[5],
                'user_profile': result[6],
                'birth_year': result[7],
                'birth_month': result[8],
                'gender': result[9],
                'user_type': result[10],
                'created_time': result[11].isoformat() if result[11] else None
            }
