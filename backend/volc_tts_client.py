import asyncio
import websockets
from websockets.client import State
import json
import os
import uuid
import logging
import struct
import base64
import gzip
import ssl
import httpx
from dotenv import load_dotenv

load_dotenv()

APPID = os.getenv("VOLC_APPID")
ACCESS_TOKEN = os.getenv("VOLC_ACCESS_KEY")
CLUSTER = os.getenv("VOLC_TTS_CLUSTER", "volc_tts")
TTS_ENDPOINT = "wss://openspeech.bytedance.com/api/v3/tts/bidirection"

# --- V3 Protocol Constants (Updated per mix.md) ---
PROTOCOL_VERSION = 1

# Message Types
MSG_FULL_CLIENT_REQUEST = 1
MSG_FULL_SERVER_RESPONSE = 9
MSG_AUDIO_ONLY_RESPONSE = 11
MSG_ERROR_RESPONSE = 15

# Message Flags
FLAG_WITH_EVENT = 4 

# Serialization
SER_RAW = 0 
SER_JSON = 1

# Compression
COMP_NONE = 0
COMP_GZIP = 1

# Event Codes (2.3)
EVENT_START_CONNECTION = 1
EVENT_FINISH_CONNECTION = 2
EVENT_CONNECTION_STARTED = 50
EVENT_CONNECTION_FAILED = 51
EVENT_CONNECTION_FINISHED = 52

EVENT_START_SESSION = 100
EVENT_CANCEL_SESSION = 101
EVENT_FINISH_SESSION = 102
EVENT_SESSION_STARTED = 150
EVENT_SESSION_CANCELED = 151
EVENT_SESSION_FINISHED = 152
EVENT_SESSION_FAILED = 153

EVENT_TASK_REQUEST = 200
EVENT_TTS_SENTENCE_START = 350
EVENT_TTS_SENTENCE_END = 351
EVENT_TTS_RESPONSE = 352

class VolcTTSClient:
    def __init__(self):
        self.websocket = None
        self.connected = False
        self.handshake_done = False # New: Handshake state guard
        self.connection_id = ""
        self.lock = asyncio.Lock()
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
    async def synthesize_http_v3(self, text: str, user_id: str = None, text_id: int = None, voice_id: int = None) -> str:
        """
        [Legacy/Fallback] Synthesize speech using V3 HTTP API (Unidirectional)
        Reserved for non-streaming scenarios or fallback.
        """
        import time
        start_time = time.time()
        
        url = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"
        headers = {
            "X-Api-App-Key": APPID, # Use App-Key for V3
            "X-Api-Access-Key": ACCESS_TOKEN,
            "X-Api-Resource-Id": "seed-tts-2.0",
            "X-Api-Connect-Id": str(uuid.uuid4()),
            "Content-Type": "application/json"
        }
        
        # HTTP Payload Structure is simpler than WS
        payload = {
            "req_params": {
                "text": text,
                "speaker": "zh_female_vv_uranus_bigtts",
                "audio_params": {
                    "format": "mp3",
                    "sample_rate": 24000
                }
            }
        }
        
        try:
            # Stream response
            async with self.http_client.stream('POST', url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    logging.error(f"[TTS HTTP] Error {response.status_code}: {error_text.decode()}")
                    return None
                
                # Concatenate all base64 audio chunks
                audio_chunks = []
                async for line in response.aiter_lines():
                    if not line.strip(): continue
                    try:
                        data = json.loads(line)
                        if data.get("code") == 0 and "data" in data:
                            audio_chunks.append(data["data"])
                    except: continue
                
                if audio_chunks:
                    # Filter out None values and concatenate
                    valid_chunks = [chunk for chunk in audio_chunks if chunk is not None]
                    if valid_chunks:
                        full_audio = "".join(valid_chunks)
                        return full_audio
                return None
                    
        except Exception as e:
            logging.error(f"[TTS HTTP] Exception: {e}")
            return None

    def _pack_header(self, msg_type, msg_flags, serialization, compression):
        b0 = 0x11 # Version 1, Header Size 1 (which means 4 bytes)
        b1 = (msg_type << 4) | msg_flags
        b2 = (serialization << 4) | compression
        b3 = 0x00
        return struct.pack('!BBBB', b0, b1, b2, b3)

    def _parse_header(self, data):
        if len(data) < 4: return 0, 0, b""
        b0, b1, b2, b3 = struct.unpack('!BBBB', data[:4])
        header_size = (b0 & 0x0F) * 4
        msg_type = b1 >> 4
        flags = b1 & 0x0F
        comp = b2 & 0x0F
        
        body = data[header_size:]
        if comp == COMP_GZIP:
             try: body = gzip.decompress(body)
             except: pass
        return msg_type, flags, body

    async def _pack_v3_packet(self, event_code, payload_json, session_id=None):
        """
        Definitive V3 Binary Packet Builder per Official Support
        - Byte 0 is always 0x11 (Header Size = 4 bytes)
        - Session/Data Class (Event 100, 102, 200) MUST include 16-byte SID prefix
        - Connection Class (Event 1, 2) uses 8-byte prefix (Header + Event)
        """
        # Header: Version 1, Header Size 1 (4 bytes)
        byte_0 = 0x11
        byte_1 = (MSG_FULL_CLIENT_REQUEST << 4) | FLAG_WITH_EVENT # 0x14
        byte_2 = (SER_JSON << 4) | COMP_NONE # 0x10
        byte_3 = 0x00
        
        header = struct.pack('!BBBB', byte_0, byte_1, byte_2, byte_3)
        body = struct.pack('!I', event_code)
        
        if session_id:
            # Session/Data Class: Fixed 16-byte SID prefix
            sid_str = session_id[:12].ljust(12, '0')
            sid_bytes = sid_str.encode('utf-8')
            body += struct.pack('!I', 12) + sid_bytes # SIDLen(4) + SID(12)
            
        json_bytes = json.dumps(payload_json).encode('utf-8')
        # PayloadLen(4) + JSON
        body += struct.pack('!I', len(json_bytes)) + json_bytes
        
        return header + body

    async def connect(self):
        """Connect to WebSocket Bidirectional Endpoint and Perform Handshake"""
        if self.connected and self.websocket and self.websocket.state == State.OPEN and self.handshake_done:
            return

        headers = {
            "X-Api-App-Key": APPID,
            "X-Api-Access-Key": ACCESS_TOKEN,
            "X-Api-Resource-Id": "seed-tts-2.0",
            "X-Api-Connect-Id": str(uuid.uuid4()),
        }
        
        try:
            self.connected = False
            self.handshake_done = False
            
            logging.info(f"Connecting to TTS V3 via {TTS_ENDPOINT}...")
            ssl_context = ssl._create_unverified_context()
            self.websocket = await websockets.connect(TTS_ENDPOINT, additional_headers=headers, ssl=ssl_context)
            self.connected = True
            
            # --- Perform StartConnection Handshake (Event 1) ---
            conn_packet = await self._pack_v3_packet(EVENT_START_CONNECTION, {})
            await self.websocket.send(conn_packet)
            
            msg = await asyncio.wait_for(self.websocket.recv(), timeout=5.0)
            m_type, flags, body = self._parse_header(msg)
            if m_type == MSG_FULL_SERVER_RESPONSE:
                event = struct.unpack('!I', body[:4])[0]
                if event == EVENT_CONNECTION_STARTED:
                    logging.info("TTS V3 WebSocket Connection & Handshake Success")
                    self.handshake_done = True
                else:
                    raise Exception(f"Connection Handshake Failed: Event {event}")
            else:
                 raise Exception(f"Connection Handshake Failed: MsgType {m_type}")
                 
        except Exception as e:
            logging.error(f"TTS Connection/Handshake Failed: {e}")
            if self.websocket: await self.websocket.close()
            self.websocket = None
            self.connected = False
            self.handshake_done = False

    async def close(self):
        if self.websocket:
            # Send FinishConnection before closing
            try:
                c_payload = {"event": EVENT_FINISH_CONNECTION}
                final_packet = await self._pack_v3_packet(EVENT_FINISH_CONNECTION, c_payload)
                await self.websocket.send(final_packet)
            except: pass
            await self.websocket.close()
            self.websocket = None
            self.connected = False
            self.handshake_done = False

    async def synthesize_stream_v3(self, text_iterator, voice_name="zh_female_vv_uranus_bigtts", user_id=None):
        """
        True Bidirectional Streaming (Persistence-Enabled)
        """
        await self.lock.acquire()
        try:
            await self.connect()
            if not self.connected or not self.handshake_done: 
                logging.error("TTS Connection not ready for session")
                return

            session_id = str(uuid.uuid4())
            
            # --- 1. Phase 1: StartSession (Event 100) ---
            start_payload = {
                "user": {"uid": user_id or "backend_user"},
                "event": EVENT_START_SESSION,
                "req_params": {
                    "speaker": voice_name,
                    "audio_params": {
                        "format": "pcm", 
                        "sample_rate": 24000,
                        "emotion": "happy",
                        "emotion_scale": 5,
                        "pitch_ratio": 1.5
                    }
                }
            }
            session_packet = await self._pack_v3_packet(EVENT_START_SESSION, start_payload, session_id=session_id)
            await self.websocket.send(session_packet)
            logging.info(f"[TTS V3] StartSession Sent (SID={session_id[:8]})")
            
            session_ready = False
            while not session_ready:
                try:
                    msg = await asyncio.wait_for(self.websocket.recv(), timeout=10.0)
                    m_type, flags, body = self._parse_header(msg)
                    if m_type == MSG_FULL_SERVER_RESPONSE:
                        event = struct.unpack('!I', body[:4])[0]
                        if event == EVENT_SESSION_STARTED:
                            logging.info("[TTS V3] SessionStarted Received")
                            session_ready = True
                        elif event == EVENT_SESSION_FAILED:
                            # Try to decode error detail if present
                            err_msg = body[8:].decode('utf-8', 'ignore') if len(body) > 8 else "Unknown Session Error"
                            logging.error(f"[TTS V3] SessionFailed: {err_msg}")
                            return
                    elif m_type == MSG_ERROR_RESPONSE:
                         logging.error(f"[TTS V3] Session Error: {body[4:].decode('utf-8', 'ignore')}")
                         return
                except Exception as e:
                    logging.error(f"[TTS V3] Session Handshake Error: {e}")
                    return

            # --- 3. Phase 3: Data Exchange ---
            audio_queue = asyncio.Queue()
            
            async def sender():
                try:
                    async for chunk in text_iterator:
                        if not chunk: continue
                        t_payload = {
                            "event": EVENT_TASK_REQUEST,
                            "req_params": {"text": chunk}
                        }
                        # OFFICIAL: TaskRequest (200) MUST also carry SID prefix in Session-Class
                        t_packet = await self._pack_v3_packet(EVENT_TASK_REQUEST, t_payload, session_id=session_id)
                        await self.websocket.send(t_packet)
                        logging.debug(f"[TTS V3] Sent TaskRequest: {chunk[:10]}...")
                    
                    # FinishSession (Event 102) - Also needs SID prefix
                    f_payload = {"event": EVENT_FINISH_SESSION}
                    f_packet = await self._pack_v3_packet(EVENT_FINISH_SESSION, f_payload, session_id=session_id)
                    await self.websocket.send(f_packet)
                    logging.info("[TTS V3] Sent FinishSession")
                except Exception as e:
                    logging.error(f"[TTS V3] Sender Error: {e}")

            async def receiver():
                try:
                    while True:
                        msg = await self.websocket.recv()
                        m_type, flags, body = self._parse_header(msg)
                        
                        # Use fixed parsing offset (20 bytes into body if Session packet)
                        # Offset 20 in body = Index 24 in Packet (Byte 25)
                        # Offset 24 in body = Index 28 in Packet (Byte 29)
                        if m_type == MSG_AUDIO_ONLY_RESPONSE:
                            if len(body) < 24: continue
                            p_len = struct.unpack('!I', body[20:24])[0]
                            chunk = body[24:24+p_len]
                            if chunk:
                                if len(chunk) > 4:
                                    logging.debug(f"[TTS V3 DEBUG] Audio Chunk (Offset 28): {chunk[:4].hex()}... Length: {len(chunk)}")
                                await audio_queue.put(chunk)
                            
                        elif m_type == MSG_FULL_SERVER_RESPONSE:
                            if len(body) < 24: continue
                            event = struct.unpack('!I', body[:4])[0]
                            if event == EVENT_SESSION_FINISHED:
                                logging.info("[TTS V3] SessionFinished Received")
                                break
                            elif event == EVENT_TTS_RESPONSE:
                                p_len = struct.unpack('!I', body[20:24])[0]
                                chunk = body[24:24+p_len]
                                if p_len > 0: 
                                    if len(chunk) > 4:
                                         logging.debug(f"[TTS V3 DEBUG] Audio Full Response Chunk: {chunk[:4].hex()}")
                                    await audio_queue.put(chunk)
                                
                        elif m_type == MSG_ERROR_RESPONSE:
                            logging.error(f"[TTS V3] Error Response: {body[4:].decode('utf-8', 'ignore')}")
                            break
                except Exception as e:
                    if self.connected: 
                        logging.error(f"[TTS V3] Receiver Error: {e}")
                    self.handshake_done = False # Mark for reconnect
                finally:
                    await audio_queue.put(None)

            sender_task = asyncio.create_task(sender())
            receiver_task = asyncio.create_task(receiver())

            while True:
                chunk = await audio_queue.get()
                if chunk is None: break
                yield chunk

            # session cleaned up, connection remains open.

        finally:
            self.lock.release()

# Global instance
global_tts_client = VolcTTSClient()
