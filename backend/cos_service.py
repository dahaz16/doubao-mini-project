#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
腾讯云 COS 服务模块

处理文件上传到腾讯云对象存储
"""
import os
import logging
from qcloud_cos import CosConfig
from qcloud_cos import CosS3Client
from .config_manager import get_config

logging.basicConfig(level=logging.INFO)

# 初始化 COS 客户端
def get_cos_client():
    """获取 COS 客户端实例"""
    secret_id = os.getenv("COS_SECRET_ID")
    secret_key = os.getenv("COS_SECRET_KEY")
    region = os.getenv("COS_REGION")
    
    if not all([secret_id, secret_key, region]):
        logging.error("❌ COS 配置缺失，请检查环境变量")
        return None
        
    config = CosConfig(Region=region, SecretId=secret_id, SecretKey=secret_key)
    client = CosS3Client(config)
    return client

def upload_audio_to_cos(audio_data: bytes, filename: str, folder: str = None) -> str:
    """
    上传音频文件到腾讯云 COS
    
    Args:
        audio_data: 音频文件二进制数据
        filename: 文件名（如 'voice_20260126_001.mp3'）
        folder: 文件夹路径（可选，如 'feedback'）
    
    Returns:
        文件的公网访问 URL
    """
    try:
        bucket = os.getenv("COS_BUCKET")
        region = os.getenv("COS_REGION")
        
        if not bucket:
            logging.error("❌ COS_BUCKET 未配置")
            return None
            
        client = get_cos_client()
        if not client:
            return None
            
        # 处理文件夹路径
        key = filename
        if folder:
            # 移除开头和结尾的斜杠
            folder = folder.strip('/')
            key = f"{folder}/{filename}"
            
        # 上传文件
        logging.info(f"📤 开始上传文件到 COS: {key}")
        response = client.put_object(
            Bucket=bucket,
            Body=audio_data,
            Key=key,
            StorageClass='STANDARD',
            EnableMD5=False
        )
        
        # 生成 URL (公有读)
        url = f"https://{bucket}.cos.{region}.myqcloud.com/{key}"
        logging.info(f"✅ 文件上传成功: {url}")
        
        return url
        
    except Exception as e:
        logging.error(f"❌ COS 上传失败: {e}")
        return None


def upload_file_to_cos(file_data: bytes, filename: str, folder: str = None) -> str:
    """
    通用上传文件到腾讯云 COS
    
    Args:
        file_data: 文件二进制数据
        filename: 文件名（包含扩展名）
        folder: 文件夹路径（可选）
    
    Returns:
        文件的公网访问 URL
    """
    return upload_audio_to_cos(file_data, filename, folder)
