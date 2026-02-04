#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
音频处理服务模块

处理音频格式转换(PCM -> MP3)
"""
import os
import logging
import io
# 延迟导入 pydub 以避免 Python 3.13 兼容性问题

logging.basicConfig(level=logging.INFO)

def convert_pcm_to_mp3(pcm_data: bytes, sample_rate: int = 16000) -> bytes:
    """
    将 PCM 音频转换为 MP3
    
    Args:
        pcm_data: PCM 音频二进制数据
        sample_rate: 采样率（默认 16000Hz）
    
    Returns:
        MP3 音频二进制数据
    """
    try:
        # 延迟导入以避免 Python 3.13 兼容性问题
        from pydub import AudioSegment
        
        logging.info(f"🔄 开始转换音频: PCM -> MP3, 大小={len(pcm_data)} bytes")
        
        # 创建 AudioSegment 对象
        # sample_width=2 (16bit), channels=1 (mono)
        audio = AudioSegment(
            data=pcm_data,
            sample_width=2,
            frame_rate=sample_rate,
            channels=1
        )
        
        # 导出为 MP3
        mp3_io = io.BytesIO()
        audio.export(mp3_io, format="mp3", bitrate="64k")
        
        mp3_data = mp3_io.getvalue()
        logging.info(f"✅ 音频转换成功: MP3 大小={len(mp3_data)} bytes")
        
        return mp3_data
        
    except Exception as e:
        logging.error(f"❌ 音频转换失败: {e}")
        # 如果转换失败，记录详细日志并抛出
        # 检查是否安装了 ffmpeg
        import shutil
        if not shutil.which("ffmpeg"):
            logging.error("❌ 未找到 ffmpeg，请先安装: brew install ffmpeg")
            
        raise e
