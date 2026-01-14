# -*- coding: utf-8 -*-
"""
============================================================================
回忆录小程序 - 后端主服务入口
============================================================================

项目描述:
    这是一个微信小程序的后端服务，用于支持回忆录采访功能。
    主要功能包括：
    1. 语音识别(ASR) - 将用户语音转换为文字
    2. 大模型对话(LLM) - 使用豆包AI进行回忆录采访对话
    3. 语音合成(TTS) - 将AI回复转换为语音

技术栈:
    - FastAPI: Web框架
    - WebSocket: 实时通信
    - 火山引擎: ASR/TTS服务
    - 豆包(Doubao): 大语言模型

作者: 项目团队
创建日期: 2026-01
============================================================================
"""

# ============================================================================
# 导入模块
# ============================================================================
from fastapi import FastAPI, HTTPException, WebSocket, Request
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from contextlib import asynccontextmanager
import os
import logging
import asyncio
import re
import urllib.parse
import uuid

# 内部模块导入
from .database import init_db, insert_record, get_records  # 数据库操作
from .ai_service import get_doubao_summary, get_doubao_chat_reply, get_doubao_chat_reply_stream  # AI服务
from .volc_service import synthesize_speech, asr_stream  # 火山引擎服务
from .volc_tts_client import VolcTTSClient  # TTS客户端

# ============================================================================
# 日志配置
# ============================================================================
logging.basicConfig(level=logging.DEBUG)

# 加载环境变量（从 .env 文件）
load_dotenv()

# ============================================================================
# 全局状态 - TTS客户端连接池
# ============================================================================
# 使用全局TTS客户端以复用WebSocket连接，减少握手延迟
global_tts_client = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    应用生命周期管理
    
    在应用启动时初始化资源，在应用关闭时清理资源。
    这是FastAPI推荐的资源管理方式。
    """
    global global_tts_client
    logging.info("正在初始化全局资源...")
    
    # 1. 初始化数据库
    init_db()
    
    # 2. 初始化TTS连接池（预连接，减少首次请求延迟）
    global_tts_client = VolcTTSClient()
    try:
        await global_tts_client.connect()
        logging.info("全局TTS客户端连接成功")
    except Exception as e:
        logging.error(f"TTS初始化错误: {e}")
    
    yield  # 应用运行期间
    
    # 清理资源
    logging.info("正在清理全局资源...")
    if global_tts_client:
        await global_tts_client.close()


# ============================================================================
# FastAPI 应用初始化
# ============================================================================
app = FastAPI(lifespan=lifespan)

# CORS（跨域资源共享）中间件配置
# 允许所有来源访问，适用于开发环境
# 生产环境应限制 allow_origins 为具体域名
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],      # 允许所有来源
    allow_credentials=True,   # 允许携带凭证
    allow_methods=["*"],      # 允许所有HTTP方法
    allow_headers=["*"],      # 允许所有请求头
)


# ============================================================================
# 全局中间件与异常处理
# ============================================================================

@app.middleware("http")
async def log_request_middleware(request: Request, call_next):
    """
    请求日志中间件
    
    记录所有进入的HTTP请求，便于调试和监控。
    """
    logging.info(f"收到请求: {request.method} {request.url}")
    try:
        response = await call_next(request)
        return response
    except Exception as e:
        logging.error(f"请求处理内部错误: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"message": str(e)})


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """
    全局异常处理器
    
    捕获所有未处理的异常，返回统一的错误响应。
    """
    logging.error(f"全局异常: {exc}", exc_info=True)
    return JSONResponse(status_code=500, content={"message": str(exc)})


# 静态文件服务（用于存放音频等资源）
app.mount("/static", StaticFiles(directory="backend/static"), name="static")


# ============================================================================
# 请求/响应模型定义
# ============================================================================

class SummaryRequest(BaseModel):
    """文本摘要请求模型"""
    text: str  # 需要摘要的文本


class SummaryResponse(BaseModel):
    """文本摘要响应模型"""
    id: int           # 记录ID
    user_input: str   # 用户输入
    ai_summary: str   # AI生成的摘要


class ChatRequest(BaseModel):
    """对话请求模型"""
    messages: list  # 消息列表，格式: [{"role": "user/assistant", "content": "..."}]


# ============================================================================
# HTTP API 端点
# ============================================================================

@app.get("/")
async def root():
    """
    健康检查端点
    
    用于验证后端服务是否正常运行。
    返回: {"status": "ok", "message": "..."}
    """
    return {"status": "ok", "message": "后端服务运行中，已启用全局连接池。"}


@app.post("/summarize", response_model=SummaryResponse)
def summarize_input(request: SummaryRequest):
    """
    文本摘要端点
    
    调用豆包AI对用户输入进行摘要，并保存到数据库。
    
    参数:
        request: 包含待摘要文本的请求体
    
    返回:
        摘要结果和记录ID
    """
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="输入文本不能为空")
    
    # 调用AI生成摘要
    summary = get_doubao_summary(request.text)
    
    # 保存到数据库
    record_id = insert_record(request.text, summary)
    
    return {
        "id": record_id,
        "user_input": request.text,
        "ai_summary": summary
    }


@app.get("/records")
def list_records():
    """
    获取所有记录
    
    从数据库读取所有的摘要记录。
    """
    return get_records()


@app.post("/chat")
def chat_with_doubao(request: ChatRequest):
    """
    同步聊天端点（已弃用，使用 /ws/chat 替代）
    
    这是一个同步的聊天端点，会阻塞等待AI回复和TTS合成完成。
    建议使用WebSocket端点 /ws/chat 以获得更好的用户体验。
    """
    if not request.messages:
        raise HTTPException(status_code=400, detail="消息列表不能为空")
    
    # 系统提示词 - 定义AI的角色
    system_prompt = "你是一名专业的回忆录采访者，请采访用户的回忆，输出的问题在60字左右。"
    messages = [{"role": "system", "content": system_prompt}] + request.messages
    
    # 获取AI回复
    reply = get_doubao_chat_reply(messages)
    
    # 语音合成
    audio_url = synthesize_speech(reply)
    
    return {
        "code": 0,
        "message": "success",
        "data": {
            "reply": reply,
            "audio": audio_url,
            "format": "mp3"
        }
    }


# ============================================================================
# WebSocket 端点
# ============================================================================

@app.websocket("/ws/chat")
async def chat_websocket_endpoint(websocket: WebSocket):
    """
    流式聊天WebSocket端点
    
    这是回忆录采访的核心端点，实现了：
    1. 接收用户消息（包含对话历史）
    2. 流式调用大模型生成回复
    3. 按句子切分，逐句合成语音并发送
    
    消息格式:
    
    接收（客户端→服务器）:
        {"messages": [{"role": "user", "content": "..."}]}
    
    发送（服务器→客户端）:
        - 文字: {"type": "text", "content": "..."}
        - 音频: {"type": "audio", "data": "<base64编码的音频>"}
        - 完成: {"type": "text_finish"}
        - 错误: {"type": "error", "message": "..."}
    """
    logging.info("[对话] ===== 新的WebSocket连接请求 =====")
    await websocket.accept()
    logging.info("[对话] WebSocket连接已接受")
    
    try:
        # 第一步：等待并接收客户端发送的消息
        logging.info("[对话] 等待客户端消息...")
        data = await websocket.receive_json()
        logging.info(f"[对话] 收到数据: {data}")
        messages = data.get("messages", [])
        
        # 第二步：添加系统提示词（如果没有）
        # 系统提示词定义了AI的角色和行为
        system_prompt = "你是一名专业的回忆录采访者，请采访用户的回忆，输出的问题在60字左右。"
        if not messages or messages[0].get("role") != "system":
            messages = [{"role": "system", "content": system_prompt}] + messages
        
        # 第三步：开始流式调用大模型
        logging.info(f"[对话] 开始调用大模型，消息数: {len(messages)}")
        stream_iterator = get_doubao_chat_reply_stream(messages)
        
        # 第四步：句子缓冲 - 用于积累文字直到遇到句子结束符
        # 目的：将完整句子发送给TTS，而不是每个字符
        sentence_buffer = ""
        sentence_endings = ["。", "!", "?", "！", "？", "\n"]  # 中英文句子结束符
        
        # 第五步：流式处理大模型输出
        for chunk in stream_iterator:
            # 5.1 立即发送文字给前端（实时显示）
            await websocket.send_json({
                "type": "text",
                "content": chunk,
            })
            logging.info(f"[对话] ===== 发送文字到前端: {chunk[:30]} =====")
            
            # 5.2 将文字添加到缓冲区
            sentence_buffer += chunk
            
            # 5.3 检测并处理完整句子
            # 使用 while 循环处理缓冲区中可能存在的多个完整句子
            while True:
                # 找到最早出现的句子结束符
                earliest_idx = -1
                earliest_ending = None
                
                for ending in sentence_endings:
                    idx = sentence_buffer.find(ending)
                    if idx != -1:
                        if earliest_idx == -1 or idx < earliest_idx:
                            earliest_idx = idx
                            earliest_ending = ending
                
                # 如果没有找到句子结束符，退出循环
                if earliest_idx == -1:
                    break
                
                # 提取完整句子
                sentence = sentence_buffer[:earliest_idx + 1].strip()
                
                # 处理句子：合成语音
                if len(sentence) > 0:
                    logging.info(f"[对话] 合成语音: {sentence[:30]}...")
                    
                    # 调用HTTP TTS服务
                    audio_base64 = await global_tts_client.synthesize_http_v3(sentence)
                    
                    if audio_base64:
                        # 发送音频给前端
                        await websocket.send_json({
                            "type": "audio",
                            "data": audio_base64
                        })
                    else:
                        logging.error(f"[对话] TTS合成失败: {sentence[:30]}")
                
                # 从缓冲区移除已处理的句子
                sentence_buffer = sentence_buffer[earliest_idx + 1:]
        
        # 第六步：处理缓冲区中剩余的文字（最后可能没有句号的部分）
        if sentence_buffer.strip():
            logging.info(f"[对话] 合成剩余文字: {sentence_buffer[:30]}...")
            audio_base64 = await global_tts_client.synthesize_http_v3(sentence_buffer.strip())
            if audio_base64:
                await websocket.send_json({
                    "type": "audio",
                    "data": audio_base64
                })
        
        # 第七步：发送完成信号
        await websocket.send_json({"type": "text_finish"})
        logging.info("[对话] 对话完成")
        
    except Exception as e:
        logging.error(f"WebSocket对话错误: {e}")
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass
    finally:
        logging.info("[对话] WebSocket连接关闭")


@app.get("/tts/stream")
async def tts_stream_endpoint(text: str):
    """
    TTS流式HTTP端点（备用方案）
    
    使用HTTP流式响应返回音频数据。
    这是WebSocket TTS的备用方案，当WebSocket不可用时使用。
    
    参数:
        text: 需要合成的文本
    
    返回:
        StreamingResponse: 流式音频数据（audio/mpeg）
    
    注意:
        此端点使用全局连接池，支持连接复用以减少延迟。
    """
    async def audio_generator():
        global global_tts_client
        if not global_tts_client:
            global_tts_client = VolcTTSClient()
        
        try:
            # 使用持久连接（synthesize_stream内部有锁保护）
            async for chunk in global_tts_client.synthesize_stream(text, keep_alive=True):
                yield chunk
        except Exception as e:
            logging.error(f"TTS流错误: {e}")
    
    return StreamingResponse(audio_generator(), media_type="audio/mpeg")


@app.websocket("/ws/asr")
async def asr_websocket_endpoint(websocket: WebSocket):
    """
    语音识别(ASR) WebSocket端点
    
    接收前端发送的音频流，转发给火山引擎ASR服务进行识别，
    并将识别结果实时返回给前端。
    
    消息格式:
    
    接收（客户端→服务器）:
        二进制音频数据（PCM格式，16kHz，16bit，单声道）
    
    发送（服务器→客户端）:
        {"text": "识别的文字", "is_final": true/false, "index": 0}
        - text: 识别出的文字
        - is_final: 是否为最终结果（句子已确认）
        - index: 句子索引，用于前端正确拼接
    """
    await websocket.accept()
    logging.info("WebSocket /ws/asr 连接已接受")
    try:
        # 调用ASR流处理函数
        await asr_stream(websocket)
    except Exception as e:
        logging.error(f"ASR错误: {e}")
    finally:
        logging.info("WebSocket /ws/asr 连接关闭")
