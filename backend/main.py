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
from typing import List, Dict, Optional, Any
from fastapi import FastAPI, HTTPException, WebSocket, Request, UploadFile, File, Form
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse, FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv
from contextlib import asynccontextmanager
import os
import logging
import asyncio
import re
import urllib.parse
import base64
import uuid

# 内部模块导入
from .database import init_db, insert_record, get_records  # 数据库操作
from .ai_service import get_doubao_summary, get_doubao_chat_reply, get_doubao_chat_reply_stream, get_doubao_response_stream  # AI服务
from .volc_service import synthesize_speech, asr_stream  # 火山引擎服务
from .volc_tts_client import VolcTTSClient  # TTS客户端
from .wechat_service import code2session, validate_wechat_config  # 微信服务
from .user_service import get_user_by_openid, create_user, update_user_info  # 用户服务

# 配置日志 - 同时输出到文件和控制台
# 确保日志文件路径绝对安全
log_file_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'backend.log')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file_path, mode='a', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
# 强制让 logger 立即生效
logging.getLogger().setLevel(logging.INFO)
logging.info(f"✅ 日志系统初始化完成，输出文件: {log_file_path}")
from .session_service import create_session, validate_session, get_session_response_id, update_session_response_id, extend_session  # Session管理
from .interview_service import save_original_text, save_original_voice  # 访谈记录服务
from .cos_service import upload_audio_to_cos  # COS服务
from .audio_service import convert_pcm_to_mp3  # 音频处理服务
from .cachepool_service import add_to_cachepool  # 缓存池服务
from .stn_database import get_latest_hint, get_previous_dialogues # 故事板支持 (v3.2)
from .stn_service import run_stn_agent_async  # Stn Agent 触发函数 (v3.2)
# v3.3 服务导入
from .intv_service import process_user_input  # 访谈员 Agent v3.3
# 管理后台服务导入
from .admin_service import router as admin_router

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


# ============================================================================
# CoT (Chain of Thought) 过滤函数
# ============================================================================
def filter_cot_markers(text: str) -> str:
    """
    过滤LLM输出中的CoT（思考链）标记和乱码
    
    豆包AI在某些推理模式下会输出内部思考标记，这些标记不应该暴露给用户。
    此函数会移除所有已知的CoT标记模式。
    
    Args:
        text: 原始LLM输出文本
    
    Returns:
        过滤后的干净文本
    """
    if not text:
        return text
    
    # 定义所有已知的CoT标记模式
    cot_patterns = [
        # SILENT标记（最常见）
        r'<\[SILENT_never_used_[a-f0-9]+\]>',
        # think标记
        r'</think_never_used_[a-f0-9]+>',
        r'<think_never_used_[a-f0-9]+>',
        # 其他可能的变体
        r'<\[THINK_[a-f0-9]+\]>',
        r'</THINK_[a-f0-9]+>',
    ]
    
    # 应用所有过滤规则
    filtered_text = text
    for pattern in cot_patterns:
        filtered_text = re.sub(pattern, '', filtered_text)
    
    # 如果过滤后文本发生了变化，记录日志
    if filtered_text != text:
        logging.warning(f"⚠️  Filtered CoT markers from text. Original length: {len(text)}, Filtered length: {len(filtered_text)}")
        logging.debug(f"Original: {text[:100]}...")
        logging.debug(f"Filtered: {filtered_text[:100]}...")
    
    return filtered_text



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
# 使用绝对路径,确保在 Docker 容器中正常工作
static_path = os.path.join(os.path.dirname(__file__), "static")
app.mount("/static", StaticFiles(directory=static_path), name="static")

# 管理后台 API 路由
app.include_router(admin_router, prefix="/admin/api", tags=["Admin"])

# 管理后台静态文件托管（需要在前端构建完成后才生效）
import os
admin_static_path = os.path.join(os.path.dirname(__file__), "static", "admin")
if os.path.exists(admin_static_path):
    # 挂载静态文件（必须放在 API 路由后面，否则会拦截 API）
    # 注意：StaticFiles 无法处理前端路由回退，我们需要手动处理
    @app.get("/admin/{path:path}")
    async def admin_spa_fallback(path: str):
        # 排除 API 路径,让它们由 API 路由处理
        if path.startswith("api/"):
            # 返回 404,让 FastAPI 继续查找其他路由
            raise HTTPException(status_code=404, detail="Not Found")
        
        # 如果是静态资源（assets 等），返回静态文件
        full_path = os.path.join(admin_static_path, path)
        if os.path.isfile(full_path):
            return FileResponse(full_path)
        # 否则返回 index.html 让前端路由接管
        return FileResponse(os.path.join(admin_static_path, "index.html"))

    # 同时也保留挂载，以便于处理根路径和其他静态资源
    app.mount("/admin", StaticFiles(directory=admin_static_path, html=True), name="admin_dashboard")
    logging.info(f"✅ 管理后台已启用: http://0.0.0.0:8000/admin")
else:
    logging.warning("⚠️  管理后台前端未构建，请先运行构建脚本")


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


class WeChatLoginRequest(BaseModel):
    """微信登录请求模型"""
    code: str  # 微信登录凭证


class UserInfoUpdateRequest(BaseModel):
    """用户信息更新请求模型"""
    user_id: str
    nickname: str = None
    avatar_url: str = None
    gender: int = None
    phone_number: str = None
    profile: str = None
    birth_year: int = None
    birth_month: int = None


class FeedbackRequest(BaseModel):
    """用户反馈请求模型"""
    user_id: str
    feedback_content: str
    feedback_voice_url: Optional[str] = None


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


@app.post("/api/wechat/login")
async def wechat_login(request: WeChatLoginRequest):
    """
    微信登录接口
    
    接收微信登录凭证 code，调用微信 API 获取 openid，
    查询或创建用户，返回用户信息。
    
    参数:
        request: 包含微信登录凭证的请求体
    
    返回:
        用户信息和登录状态
    """
    try:
        # 1. 验证微信配置
        if not validate_wechat_config():
            raise HTTPException(status_code=500, detail="微信配置不完整")
        
        # 2. 调用微信 API
        wechat_result = code2session(request.code)
        
        # 3. 检查微信 API 调用结果
        if 'errcode' in wechat_result and wechat_result['errcode'] != 0:
            raise HTTPException(
                status_code=400, 
                detail=f"微信登录失败: {wechat_result.get('errmsg')}"
            )
        
        openid = wechat_result.get('openid')
        unionid = wechat_result.get('unionid')
        
        if not openid:
            raise HTTPException(status_code=400, detail="未获取到 OpenID")
        
        # 4. 查询用户是否存在
        user = get_user_by_openid(openid)
        
        is_new_user = False
        if not user:
            # 5. 创建新用户
            user_id = create_user(openid, unionid)
            user = get_user_by_openid(openid)
            is_new_user = True
            logging.info(f"新用户注册: {user_id}")
        else:
            logging.info(f"用户登录: {user['user_id']}")
        
        # 6. 返回用户信息
        return {
            "code": 0,
            "message": "登录成功",
            "data": {
                "user_id": user['user_id'],
                "openid": user['wechat_openid'],
                "is_new_user": is_new_user,
                "user_info": user
            }
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"微信登录异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/wechat/update_userinfo")
async def update_userinfo(request: UserInfoUpdateRequest):
    """
    更新用户信息接口
    
    更新用户的昵称、头像、性别等信息。
    
    参数:
        request: 包含用户信息的请求体
    
    返回:
        更新结果
    """
    try:
        success = update_user_info(
            user_id=request.user_id,
            nickname=request.nickname,
            avatar_url=request.avatar_url,
            gender=request.gender,
            phone_number=request.phone_number,
            profile=request.profile,
            birth_year=request.birth_year,
            birth_month=request.birth_month
        )
        
        if success:
            return {
                "code": 0,
                "message": "更新成功"
            }
        else:
            raise HTTPException(status_code=400, detail="更新失败")
            
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"更新用户信息异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload_avatar")
async def upload_avatar(file: UploadFile = File(...), user_id: str = Form(...)):
    """
    上传用户头像
    """
    try:
        # 读取文件内容
        file_content = await file.read()
        
        # 生成文件名
        ext = file.filename.split('.')[-1] if '.' in file.filename else 'jpg'
        filename = f"avatar_{user_id}_{int(time.time())}.{ext}"
        
        # 上传到 COS
        avatar_url = upload_file_to_cos(file_content, filename)
        
        if not avatar_url:
            raise HTTPException(status_code=500, detail="头像上传失败")
            
        return {
            "code": 0,
            "message": "上传成功",
            "data": {
                "avatar_url": avatar_url
            }
        }
        
    except Exception as e:
        logging.error(f"头像上传异常: {e}")
        raise HTTPException(status_code=500, detail=str(e))



@app.post("/api/feedback/submit")
async def submit_feedback_endpoint(request: FeedbackRequest):
    """
    提交用户反馈
    """
    try:
        from .feedback_service import submit_feedback
        
        feedback_id = submit_feedback(
            user_id=request.user_id,
            content=request.feedback_content,
            voice_url=request.feedback_voice_url
        )
        
        return {
            "code": 200,
            "message": "反馈提交成功",
            "data": {
                "feedback_id": feedback_id
            }
        }
        
    except Exception as e:
        logging.error(f"提交反馈异常: {e}", exc_info=True)
        # Log the request data for debugging
        logging.error(f"Failed request data: user_id={request.user_id}, content={request.feedback_content}, voice_url={request.feedback_voice_url}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/upload_feedback_audio")
async def upload_feedback_audio_endpoint(file: UploadFile = File(...), user_id: str = Form(...)):
    """
    上传反馈语音文件 (自动转换 PCM -> MP3)
    """
    try:
        from .cos_service import upload_file_to_cos
        from .audio_service import convert_pcm_to_mp3
        import time
        
        # 读取文件内容 (PCM)
        pcm_content = await file.read()
        logging.info(f"🎤 [Feedback Upload] Receive PCM: {len(pcm_content)} bytes")

        if len(pcm_content) == 0:
             raise HTTPException(status_code=400, detail="文件为空")
        
        # 转换格式 (PCM -> MP3)
        try:
            mp3_data = convert_pcm_to_mp3(pcm_content)
            logging.info(f"✅ [Feedback Upload] Converted to MP3: {len(mp3_data)} bytes")
        except Exception as e:
            logging.error(f"❌ [Feedback Upload] Audio conversion failed: {e}")
            raise HTTPException(status_code=500, detail=f"音频转换失败: {str(e)}")

        # 生成文件名 (强制 .mp3) - 增加 UUID 防止并发上传文件名冲突
        import uuid
        filename = f"feedback_{user_id}_{int(time.time())}_{uuid.uuid4().hex[:8]}.mp3"
        
        # 上传到 COS
        voice_url = upload_file_to_cos(mp3_data, filename, folder="feedback")
        
        if not voice_url:
            raise HTTPException(status_code=500, detail="语音上传失败")
            
        return {
            "code": 200,
            "message": "上传成功",
            "data": {
                "voice_url": voice_url
            }
        }
        
    except Exception as e:
        logging.error(f"反馈语音上传异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/get_latest_ai_message")
async def get_latest_ai_message_endpoint(user_id: str):
    """
    获取用户最新的 AI 回复内容
    
    用于小程序采访页初始化时展示最新 AI 消息。
    
    参数:
        user_id: 用户 ID (query parameter)
    
    返回:
        {
            "code": 0,
            "message": "success",
            "data": {
                "ai_message": "最新AI回复内容" 或 null
            }
        }
    """
    try:
        from .interview_service import get_latest_ai_message
        
        ai_message = get_latest_ai_message(user_id)
        
        return {
            "code": 0,
            "message": "success",
            "data": {
                "ai_message": ai_message
            }
        }
        
    except Exception as e:
        logging.error(f"获取最新 AI 消息异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))




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
    system_prompt = '你是一名邻居小妹，在和用户进行碰面闲聊。每句话开头必须加"哥哥"。输出的内容在15字左右。'
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
    流式聊天WebSocket端点（使用 Response API）
    
    这是回忆录采访的核心端点，实现了：
    1. Session 管理（创建/验证会话）
    2. 使用 Response API 进行多轮对话
    3. 流式调用大模型生成回复
    4. 按句子切分，逐句合成语音并发送
    5. 保存对话记录到数据库
    
    消息格式:
    
    接收（客户端→服务器）:
        {
            "user_id": "用户ID",
            "session_id": "会话ID（可选）",
            "messages": [{"role": "user", "content": "..."}]
        }
    
    发送（服务器→客户端）:
        - 会话ID: {"type": "session_id", "session_id": "..."}
        - 响应ID: {"type": "response_id", "response_id": "..."}
        - 文字: {"type": "text", "content": "..."}
        - 音频: {"type": "audio", "data": "<base64编码的音频>"}
        - 完成: {"type": "text_finish"}
        - 错误: {"type": "error", "message": "..."}
    """
    logging.info("[对话] ===== 新的WebSocket连接请求 =====")
    await websocket.accept()
    logging.info("[对话] WebSocket连接已接受")
    
    try:
        # 第一步：接收客户端消息
        logging.info("[对话] 等待客户端消息...")
        data = await websocket.receive_json()
        logging.info(f"[对话] 收到数据: {data}")
        
        user_id = data.get("user_id")
        session_id = data.get("session_id")
        messages = data.get("messages", [])
        
        # 验证必需参数
        if not user_id:
            await websocket.send_json({"type": "error", "message": "缺少 user_id 参数"})
            return
        
        if not messages:
            await websocket.send_json({"type": "error", "message": "缺少 messages 参数"})
            return
        
        # 第二步：Session 管理
        if not session_id:
            # 创建新会话
            session_id = create_session(user_id)
            logging.info(f"[对话] 创建新会话: {session_id}")
            await websocket.send_json({
                "type": "session_id",
                "session_id": session_id
            })
        else:
            # 验证会话
            if not validate_session(session_id):
                # 会话无效，创建新会话
                session_id = create_session(user_id)
                logging.info(f"[对话] 会话已过期，创建新会话: {session_id}")
                await websocket.send_json({
                    "type": "session_id",
                    "session_id": session_id
                })
            else:
                # 延长会话过期时间
                extend_session(session_id)
                logging.info(f"[对话] 使用现有会话: {session_id}")
        
        # 第三步：获取用户输入
        user_input = messages[-1].get("content", "")
        if not user_input:
            await websocket.send_json({"type": "error", "message": "用户输入为空"})
            return
        
        logging.info(f"[对话] 用户输入: {user_input[:50]}...")
        
        # 保存用户输入到数据库
        save_original_text(session_id, user_id, user_input, speaker_type=0)
        
        # 添加到缓存池
        cache_result = add_to_cachepool(session_id, user_id, 0, user_input)
        logging.info(f"📝 缓存池字数: {cache_result['current_word_count']} 字")
        
        if cache_result['threshold_reached']:
            logging.info(f"🔔 缓存池已满！内容:\n{cache_result['cache_content']}")
            logging.info(f"📦 缓存池ID: {cache_result['cachepool_id']}")
            # 触发 Stn Agent
            await run_stn_agent_async(user_id, session_id, cache_result['cache_content'], cache_result['cachepool_id'])
        
        # 第四步：获取 previous_response_id
        previous_response_id = get_session_response_id(session_id)
        logging.info(f"[对话] previous_response_id: {previous_response_id[:50] if previous_response_id else 'None'}...")
        
        # 第五步：构建输入（严格遵循 PRD pc:; ot:; ht: 逻辑）
        
        # 5.1 处理 pc (前情提要)
        # 判断是否为新建 Session (没有 previous_response_id)
        pc_content = ""
        if not previous_response_id:
            pc_content = get_previous_dialogues(user_id, limit=5)
            logging.info(f"[对话] 注入 pc (前情提要): {pc_content[:50]}...")
        
        # 5.2 处理 ht (导演提示)
        ht_content = get_latest_hint(user_id)
        if ht_content:
            logging.info(f"[对话] 注入 ht (导演建议): {ht_content[:50]}...")

        # 5.3 组装 intv_input
        # 格式: pc: {previous_content}; ot: {user_original_text}; ht:{hint}
        components = []
        if pc_content:
            components.append(f"pc: {pc_content}")
        
        # ot 始终存在
        components.append(f"ot: {user_input}")
        
        if ht_content:
            components.append(f"ht: {ht_content}")
            
        full_input = "; ".join(components)
        logging.info(f"[对话] 最终组装的 intv_input: {full_input[:100]}...")
        
        # 第六步：调用 Response API
        logging.info("[对话] 开始调用 Response API...")
        stream = get_doubao_response_stream(
            input_text=full_input,
            previous_response_id=previous_response_id,
            enable_caching=False  # 暂时关闭缓存
        )
        
        # 第六步：处理流式响应
        new_response_id = None
        ai_reply = ""
        sentence_buffer = ""
        sentence_endings = ["。", "!", "?", "！", "？", "\n"]
        
        for event in stream:
            event_type = event.get("type")
            
            # 6.1 获取 response_id
            if event_type == "response_id":
                new_response_id = event["response_id"]
                logging.info(f"[对话] 获取 response_id: {new_response_id[:50]}...")
                await websocket.send_json({
                    "type": "response_id",
                    "response_id": new_response_id
                })
            
            # 6.2 处理文本内容
            elif event_type == "text":
                chunk = event["content"]
                ai_reply += chunk
                
                # 立即发送文字给前端
                await websocket.send_json({
                    "type": "text",
                    "content": chunk
                })
                logging.info(f"[对话] 发送文字: {chunk[:30]}...")
                
                # 添加到句子缓冲区
                sentence_buffer += chunk
                
                # 检测并处理完整句子
                while True:
                    earliest_idx = -1
                    earliest_ending = None
                    
                    for ending in sentence_endings:
                        idx = sentence_buffer.find(ending)
                        if idx != -1:
                            if earliest_idx == -1 or idx < earliest_idx:
                                earliest_idx = idx
                                earliest_ending = ending
                    
                    if earliest_idx == -1:
                        break
                    
                    # 提取完整句子
                    sentence = sentence_buffer[:earliest_idx + 1].strip()
                    
                    # 合成语音
                    if len(sentence) > 0:
                        logging.info(f"[对话] 合成语音: {sentence[:30]}...")
                        audio_base64 = await global_tts_client.synthesize_http_v3(sentence)
                        
                        if audio_base64:
                            await websocket.send_json({
                                "type": "audio",
                                "data": audio_base64
                            })
                        else:
                            logging.error(f"[对话] TTS合成失败: {sentence[:30]}")
                    
                    # 移除已处理的句子
                    sentence_buffer = sentence_buffer[earliest_idx + 1:]
            
            # 6.3 处理错误
            elif event_type == "error":
                error_msg = event["message"]
                logging.error(f"[对话] Response API 错误: {error_msg}")
                await websocket.send_json({
                    "type": "error",
                    "message": error_msg
                })
                return
            
            # 6.4 完成
            elif event_type == "done":
                logging.info("[对话] Response API 完成")
        
        # 第七步：处理剩余文字
        if sentence_buffer.strip():
            logging.info(f"[对话] 合成剩余文字: {sentence_buffer[:30]}...")
            audio_base64 = await global_tts_client.synthesize_http_v3(sentence_buffer.strip())
            if audio_base64:
                await websocket.send_json({
                    "type": "audio",
                    "data": audio_base64
                })
        
        # 第八步：保存 AI 回复到数据库
        if ai_reply:
            save_original_text(session_id, user_id, ai_reply, speaker_type=1)
            logging.info(f"[对话] 保存 AI 回复: {len(ai_reply)} 字")
            
            # 添加到缓存池
            cache_result = add_to_cachepool(session_id, user_id, 1, ai_reply)
            logging.info(f"📝 缓存池字数: {cache_result['current_word_count']} 字")
            
            if cache_result['threshold_reached']:
                logging.info(f"🔔 缓存池已满!内容:\n{cache_result['cache_content']}")
                logging.info(f"📦 缓存池ID: {cache_result['cachepool_id']}")
                # 触发 Stn Agent (使用异步包装)
                from .stn_service import run_stn_agent
                asyncio.create_task(run_stn_agent(user_id))
        
        
        # 第九步：更新 Session 的 response_id
        if new_response_id:
            update_session_response_id(session_id, new_response_id)
            logging.info(f"[对话] 更新 session response_id")
        
        # 第十步：发送完成信号
        await websocket.send_json({"type": "text_finish"})
        logging.info("[对话] 对话完成")
        
    except Exception as e:
        logging.error(f"WebSocket对话错误: {e}", exc_info=True)
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass
    finally:
        logging.info("[对话] WebSocket连接关闭")


@app.post("/api/upload_voice")
async def upload_voice_endpoint(
    file: UploadFile = File(...),
    user_id: str = Form(...),
    session_id: str = Form(...),
    text_id: Optional[int] = Form(None)
):
    """
    上传用户语音文件接口
    """
    try:
        logging.info(f"🎤 [Upload] 收到请求: user_id={user_id}, session_id={session_id}, text_id={text_id}, filename={file.filename}")
        
        # 读取文件内容
        pcm_data = await file.read()
        logging.info(f"🎤 [Upload] PCM 数据大小: {len(pcm_data)} bytes")
        
        if len(pcm_data) == 0:
            logging.error("❌ [Upload] 文件为空")
            return JSONResponse(status_code=400, content={"code": 400, "message": "文件为空"})
            
        # 1. 转换格式 (PCM -> MP3)
        try:
            from .audio_service import convert_pcm_to_mp3
            mp3_data = convert_pcm_to_mp3(pcm_data)
            logging.info(f"🎤 [Upload] 转换成功, MP3 大小: {len(mp3_data)} bytes")
        except Exception as e:
            logging.error(f"❌ [Upload] PCM 转换失败: {e}")
            return JSONResponse(status_code=500, content={"code": 500, "message": f"音频转换失败: {str(e)}"})
        
        # 2. 生成文件名
        import time
        import uuid
        timestamp = int(time.time())
        file_uuid = str(uuid.uuid4())[:8]
        filename = f"voice_{user_id}_{timestamp}_{file_uuid}.mp3"
        
        # 3. 上传到 COS
        from .cos_service import upload_audio_to_cos
        voice_url = upload_audio_to_cos(mp3_data, filename)
        
        if not voice_url:
            logging.error("❌ [Upload] COS 上传失败, check cos_service logs")
            return JSONResponse(status_code=500, content={"code": 500, "message": "COS 上传失败"})
            
        # 4. 保存到数据库
        try:
            from .interview_service import save_original_voice
            voice_id = save_original_voice(user_id, 0, voice_url, link_original_text_id=text_id)
            logging.info(f"✅ [Upload] 记录已存入数据库, ID={voice_id}, text_id={text_id}, URL={voice_url}")
        except Exception as e:
            logging.error(f"❌ [Upload] 数据库保存失败: {e}")
            return JSONResponse(status_code=500, content={"code": 500, "message": f"数据库保存失败: {str(e)}"})
        
        return {
            "code": 0,
            "message": "上传成功",
            "data": {
                "voice_url": voice_url,
                "voice_id": voice_id
            }
        }
    except Exception as e:
        logging.error(f"💥 [Upload] 未捕获的错误: {e}", exc_info=True)
        return JSONResponse(status_code=500, content={"code": 500, "message": str(e)})


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


# ============================================================================
# v3.3 WebSocket 端点
# ============================================================================

@app.websocket("/ws/interview")
async def chat_websocket_v33_endpoint(websocket: WebSocket):
    """
    v3.3 流式聊天 WebSocket 端点
    
    使用新的 Intv Agent 服务，基于 narration_status 表进行 Session 管理。
    
    消息格式:
    
    接收（客户端→服务器）:
        {
            "user_id": "用户ID",
            "text": "用户输入文本",
            "has_voice": false
        }
    
    发送（服务器→客户端）:
        - 开始: {"type": "start"}
        - 文字: {"type": "text", "content": "..."}
        - 音频: {"type": "audio", "data": "<base64>"}
        - 完成: {"type": "done", "full_text": "..."}
        - 错误: {"type": "error", "message": "..."}
    """
    logging.info("[v3.3] ===== 新的 WebSocket 连接请求 =====")
    await websocket.accept()
    logging.info("[v3.3] WebSocket 连接已接受")
    
    try:
        # 接收客户端消息
        data = await websocket.receive_json()
        logging.info(f"[v3.3] 收到数据: {data}")
        
        user_id = data.get("user_id")
        user_text = data.get("text", "")
        has_voice = data.get("has_voice", False)
        
        if not user_id:
            await websocket.send_json({"type": "error", "message": "缺少 user_id 参数"})
            return
        
        if not user_text.strip():
            await websocket.send_json({"type": "error", "message": "输入文本为空"})
            return
        
        logging.info(f"[v3.3] 用户输入: {user_text[:50]}...")
        
        # --- TTS Streaming Setup ---
        text_queue = asyncio.Queue()
        
        async def text_iterator():
            while True:
                chunk = await text_queue.get()
                if chunk is None:
                    break
                yield chunk

        # Start TTS Task
        tts_generator = global_tts_client.synthesize_stream_v3(text_iterator())
        
        # Audio Receiver Task: Sends audio to Frontend & Accumulates for Saving
        full_audio_buffer = bytearray()
        
        async def tts_receiver_task():
            nonlocal full_audio_buffer
            audio_chunk_count = 0
            try:
                logging.info("[v3.3] TTS Receiver Task Started")
                # We need to send "start" signal for audio? No, frontend handles it.
                async for audio_chunk in tts_generator:
                    if audio_chunk:
                        audio_chunk_count += 1
                        full_audio_buffer.extend(audio_chunk)
                        # Convert to base64 for websocket
                        b64_data = base64.b64encode(audio_chunk).decode('utf-8')
                        logging.info(f"[v3.3] Sending audio chunk #{audio_chunk_count}: {len(audio_chunk)} bytes (b64 len: {len(b64_data)})")
                        await websocket.send_json({"type": "audio", "data": b64_data})
                logging.info(f"[v3.3] TTS Receiver Task Finished. Total chunks: {audio_chunk_count}")
            except Exception as e:
                logging.error(f"[v3.3] TTS Receiver Error: {e}", exc_info=True)


        tts_task = asyncio.create_task(tts_receiver_task())
        
        # --- Main LLM Loop ---
        ai_text_id = None
        full_ai_response = ""
        sentence_buffer = ""
        
        async for event in process_user_input(user_id, user_text, has_voice):
            event_type = event.get("type")
            
            if event_type == "start":
                await websocket.send_json({"type": "start"})

            elif event_type == "session_id":
                await websocket.send_json({"type": "session_id", "session_id": event.get("session_id")})
            
            elif event_type == "user_text_id":
                await websocket.send_json({"type": "user_text_id", "text_id": event.get("text_id")})
            
            elif event_type == "text":
                chunk = event.get("content", "")
                
                # ⚠️  过滤CoT标记
                chunk = filter_cot_markers(chunk)
                
                # 只有在过滤后chunk不为空时才处理
                if chunk:
                    full_ai_response += chunk
                    
                    # Send text to frontend
                    await websocket.send_json({"type": "text", "content": chunk})
                    
                    # Buffer sentences to avoid TTS stuttering
                    sentence_buffer += chunk
                    if any(p in sentence_buffer for p in "。！？；\n") or len(sentence_buffer) >= 60:
                        await text_queue.put(sentence_buffer)
                        sentence_buffer = ""
            
            elif event_type == "done":
                ai_text_id = event.get("ai_text_id")
                # Flush remaining buffer
                if sentence_buffer:
                    await text_queue.put(sentence_buffer)
                # Signal TTS to finish
                await text_queue.put(None) 
                
            elif event_type == "error":
                await websocket.send_json({"type": "error", "message": event.get("message")})
                await text_queue.put(None) # Ensure TTS stops
                return
        
        # Wait for TTS to finish
        await tts_task
        
        # --- Post-process: Save Audio to COS & DB ---
        logging.info(f"[v3.4] 🎵 开始处理 AI 音频保存流程...")
        logging.info(f"[v3.4] 📊 full_audio_buffer 大小: {len(full_audio_buffer) if full_audio_buffer else 0} bytes")
        logging.info(f"[v3.4] 📊 ai_text_id: {ai_text_id}")
        
        if full_audio_buffer and ai_text_id:
            try:
                from datetime import datetime
                from io import BytesIO
                from pydub import AudioSegment
                from .cos_service import upload_audio_to_cos
                from .interview_service import save_original_voice
                
                logging.info(f"[v3.4] ✅ 条件满足,开始转换和上传...")
                logging.info(f"[v3.4] 📤 PCM 转换 MP3 中... 大小: {len(full_audio_buffer)} bytes")
                
                # 1. 将 raw PCM 转为 AudioSegment
                # 采样率需与 TTS 配置一致 (24000), 16bit(sample_width=2), 单声道
                audio_segment = AudioSegment(
                    data=bytes(full_audio_buffer),
                    sample_width=2,
                    frame_rate=24000,
                    channels=1
                )
                logging.info(f"[v3.4] ✅ AudioSegment 创建成功")
                
                # 2. 导出为 MP3
                mp3_fp = BytesIO()
                audio_segment.export(mp3_fp, format="mp3", bitrate="128k")
                mp3_data = mp3_fp.getvalue()
                logging.info(f"[v3.4] ✅ MP3 导出成功, 大小: {len(mp3_data)} bytes")
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
                filename = f"tts/{user_id}/{timestamp}.mp3"
                logging.info(f"[v3.4] 📝 文件名: {filename}")
                
                # 3. 上传 MP3 到 COS
                logging.info(f"[v3.4] 🚀 开始上传到 COS...")
                audio_url = upload_audio_to_cos(mp3_data, filename)
                logging.info(f"[v3.4] 📊 COS 上传结果: {audio_url if audio_url else 'FAILED'}")
                
                if audio_url:
                    logging.info(f"[v3.4] ✅ COS 上传成功: {audio_url[:80]}...")
                    logging.info(f"[v3.4] 💾 开始保存到数据库...")
                    logging.info(f"[v3.4] 📊 保存参数: user_id={user_id}, speaker_type=1, text_id={ai_text_id}")
                    
                    voice_id = save_original_voice(user_id, speaker_type=1, audio_url=audio_url, link_original_text_id=ai_text_id)
                    
                    logging.info(f"[v3.4] ✅✅✅ AI 音频保存完全成功! voice_id={voice_id}, url={audio_url}")
                    logging.info(f"[v3.4] 📊 最终统计: PCM={len(full_audio_buffer)}B, MP3={len(mp3_data)}B, 压缩率={len(mp3_data)/len(full_audio_buffer)*100:.1f}%")
                else:
                    logging.error(f"[v3.4] ❌❌❌ COS 上传失败! audio_url 为空")
                    logging.error(f"[v3.4] 📊 失败信息: user_id={user_id}, text_id={ai_text_id}, mp3_size={len(mp3_data)}")
                    
            except Exception as e:
                logging.error(f"[v3.4] ❌❌❌ Audio Save/Convert Error: {e}")
                logging.error(f"[v3.4] 📊 错误上下文: user_id={user_id}, text_id={ai_text_id}, buffer_size={len(full_audio_buffer) if full_audio_buffer else 0}")
                import traceback
                logging.error(f"[v3.4] 📚 完整堆栈:\n{traceback.format_exc()}")
        else:
            if not full_audio_buffer:
                logging.warning(f"[v3.4] ⚠️ full_audio_buffer 为空,跳过音频保存")
            if not ai_text_id:
                logging.warning(f"[v3.4] ⚠️ ai_text_id 为空,跳过音频保存")
        
        await websocket.send_json({"type": "text_finish"})
            

        logging.info("[v3.3] 对话完成")
        
    except Exception as e:
        logging.error(f"[v3.3] WebSocket 错误: {e}", exc_info=True)
        try:
            await websocket.send_json({"type": "error", "message": str(e)})
        except:
            pass
    finally:
        logging.info("[v3.3] WebSocket 连接关闭")


# ============================================================================
# Writing API Endpoints (v0.5 - 我的故事页)
# ============================================================================

@app.get("/api/writing/status")
async def get_writing_status_endpoint(user_id: str):
    """
    获取写作状态
    
    返回:
        {
            "code": 0,
            "message": "success",
            "data": {
                "ready": bool,  # 是否可以写作
                "is_first_time": bool,  # 是否首次写作
                "words_count": int,  # 当前缓存池字数
                "threshold": int,  # 触发阈值
                "writing_state": int  # 0=pending, 1=writing
            }
        }
    """
    try:
        from .wtr_service import check_writing_readiness
        from .wtr_cachepool_service import get_writing_status
        
        readiness = check_writing_readiness(user_id)
        status = get_writing_status(user_id)
        
        return {
            "code": 0,
            "message": "success",
            "data": {
                **readiness,
                "writing_state": status['writing_state'] if status else 0
            }
        }
        
    except Exception as e:
        logging.error(f"获取写作状态异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/writing/trigger")
async def trigger_writing_endpoint(request: dict):
    """
    触发写作任务
    
    请求体:
        {
            "user_id": "用户ID"
        }
    
    返回:
        {
            "code": 0,
            "message": "success",
            "data": {
                "success": bool,
                "message": str,
                "articles_created": int
            }
        }
    """
    try:
        user_id = request.get("user_id")
        if not user_id:
            raise HTTPException(status_code=400, detail="缺少 user_id 参数")
        
        logging.info(f"📝 收到写作触发请求: user_id={user_id}")
        
        from .wtr_service import run_wtr_agent
        
        result = await run_wtr_agent(user_id)
        
        return {
            "code": 0,
            "message": "success",
            "data": result
        }
        
    except Exception as e:
        logging.error(f"触发写作异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/memoir/chapters")
async def get_memoir_chapters_endpoint(user_id: str):
    """
    获取用户的回忆录章节列表
    
    返回:
        {
            "code": 0,
            "message": "success",
            "data": {
                "chapters": [
                    {
                        "chapter_id": int,
                        "link_stage_id": int,
                        "chapter_name": str,
                        "chapter_sort_num": int,
                        "created_time": str
                    }
                ]
            }
        }
    """
    try:
        from .wtr_database import get_chapters_by_user
        
        chapters = get_chapters_by_user(user_id)
        
        # 转换 datetime 为字符串
        for chapter in chapters:
            if chapter.get('created_time'):
                chapter['created_time'] = chapter['created_time'].isoformat()
        
        return {
            "code": 0,
            "message": "success",
            "data": {
                "chapters": chapters
            }
        }
        
    except Exception as e:
        logging.error(f"获取章节列表异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/api/memoir/articles")
async def get_memoir_articles_endpoint(user_id: str, chapter_id: Optional[int] = None):
    """
    获取回忆录文章列表
    
    参数:
        user_id: 用户 ID
        chapter_id: 章节 ID（可选，不传则返回所有文章）
    
    返回:
        {
            "code": 0,
            "message": "success",
            "data": {
                "articles": [
                    {
                        "section_id": int,
                        "topic_id": int,
                        "chapter_id": int,
                        "chapter_name": str,  # 仅当不指定 chapter_id 时返回
                        "section_name": str,
                        "section_content": str,
                        "section_sort_num": int,
                        "created_time": str
                    }
                ]
            }
        }
    """
    try:
        from .wtr_database import get_articles_by_chapter, get_all_articles_by_user
        
        if chapter_id:
            articles = get_articles_by_chapter(chapter_id)
        else:
            articles = get_all_articles_by_user(user_id)
        
        # 转换 datetime 为字符串
        for article in articles:
            if article.get('created_time'):
                article['created_time'] = article['created_time'].isoformat()
        
        return {
            "code": 0,
            "message": "success",
            "data": {
                "articles": articles
            }
        }
        
    except Exception as e:
        logging.error(f"获取文章列表异常: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

