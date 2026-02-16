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
        logging.info(f"[COS] 🚀 开始上传文件...")
        logging.info(f"[COS] 📊 文件大小: {len(audio_data)} bytes")
        logging.info(f"[COS] 📝 文件名: {filename}")
        logging.info(f"[COS] 📁 文件夹: {folder if folder else '(根目录)'}")
        
        bucket = os.getenv("COS_BUCKET")
        region = os.getenv("COS_REGION")
        
        logging.info(f"[COS] 🔧 环境变量检查:")
        logging.info(f"[COS]   - COS_BUCKET: {bucket if bucket else '❌ 未设置'}")
        logging.info(f"[COS]   - COS_REGION: {region if region else '❌ 未设置'}")
        logging.info(f"[COS]   - COS_SECRET_ID: {'✅ 已设置' if os.getenv('COS_SECRET_ID') else '❌ 未设置'}")
        logging.info(f"[COS]   - COS_SECRET_KEY: {'✅ 已设置' if os.getenv('COS_SECRET_KEY') else '❌ 未设置'}")
        
        if not bucket:
            logging.error("[COS] ❌ COS_BUCKET 未配置")
            return None
            
        client = get_cos_client()
        if not client:
            logging.error("[COS] ❌ 无法创建 COS 客户端")
            return None
        
        logging.info(f"[COS] ✅ COS 客户端创建成功")
            
        # 处理文件夹路径
        key = filename
        if folder:
            # 移除开头和结尾的斜杠
            folder = folder.strip('/')
            key = f"{folder}/{filename}"
        
        logging.info(f"[COS] 📍 最终 Key: {key}")
            
        # 上传文件
        logging.info(f"[COS] 📤 开始上传到 COS: {key}")
        response = client.put_object(
            Bucket=bucket,
            Body=audio_data,
            Key=key,
            StorageClass='STANDARD',
            EnableMD5=False
        )
        
        logging.info(f"[COS] 📊 上传响应: {response}")
        
        # 生成 URL (公有读)
        url = f"https://{bucket}.cos.{region}.myqcloud.com/{key}"
        logging.info(f"[COS] ✅✅✅ 文件上传成功!")
        logging.info(f"[COS] 🔗 URL: {url}")
        
        return url
        
    except Exception as e:
        logging.error(f"[COS] ❌❌❌ COS 上传失败: {e}")
        logging.error(f"[COS] 📊 失败上下文: filename={filename}, folder={folder}, data_size={len(audio_data) if audio_data else 0}")
        import traceback
        logging.error(f"[COS] 📚 完整堆栈:\n{traceback.format_exc()}")
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
