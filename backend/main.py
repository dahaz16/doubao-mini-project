from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from dotenv import load_dotenv
from .database import init_db, insert_record, get_records
from .ai_service import get_doubao_summary, get_doubao_chat_reply
from .volc_service import synthesize_speech
import os

# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# Mount Static Files for Audio
app.mount("/static", StaticFiles(directory="backend/static"), name="static")

# Initialize database on startup
init_db()

# ... (Summary/Records endpoints omitted for brevity, ensure they are kept or I use start/end carefully)
# Actually, I should use `replace_file_content` carefully to not delete lines I don't see in the context, 
# but I'm rewriting the top imports and adding the WS route at the bottom?
# Let's search-replace imports first, then add the route.

# Wait, I can do it in one go if I include enough context or just add the route.
# I will use `replace_file_content` to add imports at top, then another call to add route.
# Or just one call if I Replace the whole file? No, too risky.
# Let's add imports first.


# Load environment variables from .env file
load_dotenv()

app = FastAPI()

# Mount Static Files for Audio
app.mount("/static", StaticFiles(directory="backend/static"), name="static")

# Initialize database on startup
init_db()

class SummaryRequest(BaseModel):
    text: str

class SummaryResponse(BaseModel):
    id: int
    user_input: str
    ai_summary: str

@app.get("/")
def read_root():
    return {"Hello": "World", "Status": "Doubao AI Project Running"}

@app.post("/summarize", response_model=SummaryResponse)
def summarize_input(request: SummaryRequest):
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Input text cannot be empty")

    # 1. Get summary from AI
    summary = get_doubao_summary(request.text)

    # 2. Save to database
    record_id = insert_record(request.text, summary)

    return {
        "id": record_id,
        "user_input": request.text,
        "ai_summary": summary
    }

@app.get("/records")
def list_records():
    return get_records()

class ChatRequest(BaseModel):
    messages: list

@app.post("/chat")
def chat_with_doubao(request: ChatRequest):
    if not request.messages:
        raise HTTPException(status_code=400, detail="Messages list cannot be empty")
    
    # 1. Get AI Reply
    reply = get_doubao_chat_reply(request.messages)
    
    # 2. Synthesize Speech (TTS)
    # We strip potential markdown or extra spaces before TTS
    clean_text = reply.replace("*", "").strip() 
    audio_url = synthesize_speech(clean_text)
    
    # Prepend base url if path is relative
    if audio_url:
        audio_url = f"http://127.0.0.1:8000{audio_url}" # Adjust for real logic if needed

    return {
        "reply": reply,
        "audio_url": audio_url
    }

from .volc_service import asr_stream

@app.websocket("/ws/asr")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    try:
        await asr_stream(websocket)
    except Exception as e:
        print(f"WebSocket Error: {e}")
        # Allow closing to happen naturally

