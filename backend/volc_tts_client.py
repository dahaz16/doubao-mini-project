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

# --- V3 Protocol Constants ---
PROTOCOL_VERSION = 1
HEADER_SIZE = 1

# Message Types
MSG_FULL_CLIENT_REQUEST = 1   # 0b0001
MSG_AUDIO_ONLY_REQUEST = 2    # 0b0010
MSG_FULL_SERVER_RESPONSE = 9  # 0b1001
MSG_AUDIO_ONLY_RESPONSE = 11  # 0b1011
MSG_ERROR_RESPONSE = 15       # 0b1111

# Message Flags
FLAG_NO_SEQUENCE = 0      # 0b0000
FLAG_WITH_SEQUENCE = 1    # 0b0001 (For Audio-only mostly? No, usually Events use 0000 or specific)
FLAG_WITH_EVENT = 0      # Actually, documentation says specific flags per type.
# Full Client Request: 0b0100 (With Event)
# StartSession is Full Client Request

# Serialization
SER_RAW = 0 # 0b0000
SER_JSON = 1 # 0b0001

# Compression
COMP_NONE = 0
COMP_GZIP = 1

# Events
EVENT_START_CONNECTION = 1
EVENT_FINISH_CONNECTION = 2
EVENT_CONNECTION_STARTED = 50
EVENT_CONNECTION_FAILED = 51

EVENT_START_SESSION = 100
EVENT_FINISH_SESSION = 102
EVENT_SESSION_STARTED = 150
EVENT_SESSION_FINISHED = 152
EVENT_SESSION_FAILED = 153

EVENT_TASK_REQUEST = 200
EVENT_TTS_SENTENCE_START = 350
EVENT_TTS_SENTENCE_END = 351
EVENT_TTS_RESPONSE = 352  # Audio detected as event

class VolcTTSClient:
    def __init__(self):
        self.websocket = None
        self.connected = False
        self.connection_id = ""
        self.lock = asyncio.Lock() # Add Lock for shared connection
        self.http_client = httpx.AsyncClient(timeout=30.0)
        
    async def synthesize_http_v3(self, text: str) -> str:
        """
        Synthesize speech using V3 HTTP API
        Returns: base64 encoded audio string, or None if failed
        """
        url = "https://openspeech.bytedance.com/api/v3/tts/unidirectional"
        headers = {
            "X-Api-App-Id": APPID,
            "X-Api-Access-Key": ACCESS_TOKEN,
            "X-Api-Resource-Id": "seed-tts-2.0",
            "X-Api-Cluster-Id": "volcano_tts",
            "Content-Type": "application/json"
        }
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
        
        logging.info(f"[TTS HTTP] ===== USING SPEAKER: {payload['req_params']['speaker']} =====")
        logging.info(f"[TTS HTTP] ===== RESOURCE ID: seed-tts-2.0 =====")
        logging.info(f"[TTS HTTP] ===== CLUSTER ID: volcano_tts =====")
        logging.info(f"[TTS HTTP] ===== FULL PAYLOAD: {payload} =====")
        
        try:
            logging.info(f"[TTS HTTP] Synthesizing: {text[:50]}...")
            
            # Stream response
            async with self.http_client.stream('POST', url, headers=headers, json=payload) as response:
                if response.status_code != 200:
                    error_text = await response.aread()
                    logging.error(f"[TTS HTTP] HTTP {response.status_code}: {error_text.decode()}")
                    return None
                
                # Concatenate all base64 audio chunks
                audio_chunks = []
                async for line in response.aiter_lines():
                    if not line.strip():
                        continue
                    
                    try:
                        data = json.loads(line)
                        if data.get("code") == 0 and "data" in data:
                            audio_chunks.append(data["data"])
                        elif data.get("code") != 0:
                            logging.error(f"[TTS HTTP] API Error in stream: {data}")
                    except json.JSONDecodeError as e:
                        logging.warning(f"[TTS HTTP] Failed to parse line: {line[:100]}... Error: {e}")
                        continue
                
                if audio_chunks:
                    # Filter out None values and concatenate
                    valid_chunks = [chunk for chunk in audio_chunks if chunk is not None]
                    if valid_chunks:
                        full_audio = "".join(valid_chunks)
                        logging.info(f"[TTS HTTP] Success! Total audio length: {len(full_audio)} chars from {len(valid_chunks)} chunks")
                        return full_audio
                    else:
                        logging.error("[TTS HTTP] No valid audio data received (all chunks were None)")
                        return None
                else:
                    logging.error("[TTS HTTP] No audio data received")
                    return None
                    
        except Exception as e:
            logging.error(f"[TTS HTTP] Exception: {e}")
            import traceback
            logging.error(traceback.format_exc())
            return None
        
    def _pack_header(self, msg_type, specific_flags, serialization, compression):
        b0 = (PROTOCOL_VERSION << 4) | HEADER_SIZE
        b1 = (msg_type << 4) | specific_flags
        b2 = (serialization << 4) | compression
        b3 = 0x00 # Reserved
        return struct.pack('!BBBB', b0, b1, b2, b3)

    async def connect(self):
        if self.connected and self.websocket:
            return

        headers = {
            "X-Api-App-Key": APPID,
            "X-Api-Access-Key": ACCESS_TOKEN,
            "X-Api-Resource-Id": "seed-tts-2.0",
            "X-Api-Connect-Id": str(uuid.uuid4())
        }
        
        try:
            logging.info(f"Connecting to TTS via {TTS_ENDPOINT}...")
            # Use unverified context to bypass potential proxy SSL issues
            ssl_context = ssl._create_unverified_context()
            
            self.websocket = await websockets.connect(TTS_ENDPOINT, additional_headers=headers, ssl=ssl_context)
            
            # --- Handshake: Send StartConnection ---
            await self._send_start_connection()
            
            # --- Handshake: Wait for ConnectionStarted ---
            success = await self._wait_for_connection_started()
            if success:
                self.connected = True
                logging.info("TTS V3 Handshake Success")
            else:
                logging.error("TTS V3 Handshake Failed")
                await self.close()
                
        except Exception as e:
            logging.error(f"TTS Connection Failed: {e}")
            self.websocket = None
            self.connected = False

    async def _send_start_connection(self):
        # Header: FullClient(1) | Flag(4-Event) | JSON(1) | None(0)
        header = self._pack_header(MSG_FULL_CLIENT_REQUEST, 0b0100, SER_JSON, COMP_NONE)
        
        event_bytes = struct.pack('!I', EVENT_START_CONNECTION)
        
        # Payload is empty JSON "{}"
        payload = b"{}"
        payload_len = struct.pack('!I', len(payload))
        
        # Packet: Header + Event + PayloadLen + Payload
        packet = header + event_bytes + payload_len + payload
        await self.websocket.send(packet)
        logging.info("[TTS] Sent StartConnection")

    async def _wait_for_connection_started(self):
        try:
            # We assume the first message is ConnectionStarted
            resp = await self.websocket.recv()
            msg_type, flags, payload_data = self._parse_header(resp)
            
            if msg_type == MSG_FULL_SERVER_RESPONSE:
                # Parse Event
                event_type = struct.unpack('!I', payload_data[:4])[0]
                if event_type == EVENT_CONNECTION_STARTED:
                    # Parse Connection ID
                    offset = 4
                    conn_id_len = struct.unpack('!I', payload_data[offset:offset+4])[0]
                    offset += 4
                    self.connection_id = payload_data[offset:offset+conn_id_len].decode('utf-8')
                    logging.info(f"[TTS] ConnectionStarted (ID: {self.connection_id})")
                    return True
                elif event_type == EVENT_CONNECTION_FAILED:
                    logging.error("[TTS] ConnectionFailed Event received")
                    return False
            
            logging.error(f"[TTS] Unexpected handshake response type: {msg_type}")
            return False
            
        except Exception as e:
            logging.error(f"[TTS] Handshake Error: {e}")
            return False

    async def close(self):
        if self.websocket:
            try:
                # Try sending FinishConnection
                pass 
            except: pass
            await self.websocket.close()
        self.websocket = None
        self.connected = False
        logging.info("TTS V3 WebSocket Closed")

    async def synthesize(self, text, seq_id=0):
        if not self.connected or not self.websocket:
            await self.connect()
            if not self.connected: return

        session_id = str(uuid.uuid4())
        
        # --- Send StartSession ---
        req_params = {
            "text": text,
            "speaker": "zh_female_vv_uranus_bigtts", # Vivi 2.0
            "audio_params": {
                "format": "pcm",  # Changed to PCM for smooth streaming
                "sample_rate": 24000
            }
        }
        
        meta_payload = {
            "user": {"uid": "user_backend"},
            "event": 100, # Event_StartSession
            "req_params": req_params
        }
        json_bytes = json.dumps(meta_payload).encode('utf-8')
        
        # Header: FullClient(1) | Flag(4-Event) | JSON(1) | None(0)
        header = self._pack_header(MSG_FULL_CLIENT_REQUEST, 0b0100, SER_JSON, COMP_NONE)
        
        event_bytes = struct.pack('!I', EVENT_START_SESSION)
        
        sess_id_bytes = session_id.encode('utf-8')
        sess_id_len_bytes = struct.pack('!I', len(sess_id_bytes))
        
        meta_len_bytes = struct.pack('!I', len(json_bytes))
        
        # Packet: Header + Event(4) + SessIDLen(4) + SessID + MetaLen(4) + Meta
        packet = header + event_bytes + sess_id_len_bytes + sess_id_bytes + meta_len_bytes + json_bytes
        await self.websocket.send(packet)
        logging.info(f"[TTS] Sent StartSession (SessionID: {session_id[:8]})")

        # --- Send TaskRequest (Text) ---
        # Document says: text applies at TaskRequest
        task_payload = {
            "req_params": {
                "text": text
            }
        }
        task_json = json.dumps(task_payload).encode('utf-8')
        
        # Header for TaskRequest
        header_task = self._pack_header(MSG_FULL_CLIENT_REQUEST, 0b0100, SER_JSON, COMP_NONE)
        event_task = struct.pack('!I', EVENT_TASK_REQUEST)
        task_len_bytes = struct.pack('!I', len(task_json))
        
        # Packet: Header + Event + SessIDLen + SessID + PayloadLen + Payload
        # Note: TaskRequest also needs SessionID to know context
        packet_task = header_task + event_task + sess_id_len_bytes + sess_id_bytes + task_len_bytes + task_json
        await self.websocket.send(packet_task)
        logging.info(f"[TTS] Sent TaskRequest (Text: {text[:10]}...)")

        # --- Receive Loop ---
        while True:
            try:
                resp = await self.websocket.recv()
                msg_type, flags, body = self._parse_header(resp)
                logging.info(f"[TTS_DEBUG] Recv Packet: Type={msg_type}, Flags={flags}, BodyLen={len(body)}")
                
                # Case 1: Audio Only Response (No Event) - Defined in binary frame table
                if msg_type == MSG_AUDIO_ONLY_RESPONSE:
                    # Body Structure: SessionIDLen(4) + SessionID + AudioLen(4) + Audio
                    # NOTE: If flags has event bit, likely contains event?
                    # "Audio, no event": Header + SessIDLen + SessID + PayloadLen + Payload
                    offset = 0
                    if len(body) < 4: 
                        logging.warning("[TTS_DEBUG] Audio packet body too short (no sess_id_len)")
                        continue
                    s_len = struct.unpack('!I', body[offset:offset+4])[0]
                    offset += 4 + s_len # Skip SessionID
                    
                    if len(body) < offset + 4: 
                        logging.warning("[TTS_DEBUG] Audio packet body too short (no audio_len)")
                        continue
                    a_len = struct.unpack('!I', body[offset:offset+4])[0]
                    offset += 4
                    audio_chunk = body[offset:offset+a_len]
                    
                    if audio_chunk:
                        logging.info(f"[TTS_DEBUG] Yielding Audio Chunk ({len(audio_chunk)} bytes)")
                        encoded = base64.b64encode(audio_chunk).decode('utf-8')
                        yield encoded
                        
                # Case 2: Full Server Response (Events)
                elif msg_type == MSG_FULL_SERVER_RESPONSE:
                    # Body Structure: Event(4) + SessionIDLen(4) + SessionID + PayloadLen(4) + Payload
                    event_type = struct.unpack('!I', body[:4])[0]
                    logging.info(f"[TTS_DEBUG] Event Received: {event_type}")
                    
                    if event_type == EVENT_SESSION_FINISHED:
                        logging.info(f"[TTS] SessionFinished for {session_id[:8]}")
                        break # Done with this sentence
                        
                    elif event_type == EVENT_SESSION_FAILED:
                         logging.error("[TTS] SessionFailed")
                         # Try to parse error message if possible
                         break
                         
                    elif event_type == EVENT_TTS_RESPONSE:
                        # Sometimes Audio comes as Event 
                        # Structure: Event(4) + SessIDLen(4) + SessID + AudioLen(4) + Audio
                        offset = 4
                        s_len = struct.unpack('!I', body[offset:offset+4])[0]
                        offset += 4 + s_len
                        a_len = struct.unpack('!I', body[offset:offset+4])[0]
                        offset += 4
                        audio_chunk = body[offset:offset+a_len]
                        if audio_chunk:
                             logging.info(f"[TTS_DEBUG] Yielding Audio (Event) ({len(audio_chunk)} bytes)")
                             encoded = base64.b64encode(audio_chunk).decode('utf-8')
                             yield encoded
                             
            except Exception as e:
                logging.error(f"[TTS] Recv Error: {e}")
                self.connected = False
                break

    async def synthesize_stream(self, text, seq_id=0, keep_alive=True):
        """
        [Mode B: HTTP Streaming Support]
        Generator that yields RAW AUDIO BYTES (MP3/PCM) for StreamingResponse.
        Different from synthesize() which yields Base64 for WebSocket.
        
        Args:
            keep_alive (bool): If True, does not close the websocket after session finish.
        """
        # Use Lock to prevent overlapping sessions on shared WebSocket
        async with self.lock:
            # Connect if not already connected
            is_open = self.websocket and self.websocket.state == State.OPEN
            if not self.connected or not is_open:
                 logging.info("[TTS-Stream] Connecting or Reconnecting socket (State: %s)...", 
                              self.websocket.state if self.websocket else "None")
                 await self.connect()
                 if not self.connected: 
                     logging.error("[TTS-Stream] Connection failed even after reconnect")
                     return

            session_id = str(uuid.uuid4())
            
            # --- Send StartSession ---
            req_params = {
                "text": text,
                "speaker": "zh_female_vv_uranus_bigtts",
                "audio_params": {
                    "format": "mp3", 
                    "sample_rate": 24000
                }
            }
            
            meta_payload = {
                "user": {"uid": "user_backend"},
                "event": 100, 
                "req_params": req_params
            }
            json_bytes = json.dumps(meta_payload).encode('utf-8')
            
            header = self._pack_header(MSG_FULL_CLIENT_REQUEST, 0b0100, SER_JSON, COMP_NONE)
            event_bytes = struct.pack('!I', EVENT_START_SESSION)
            sess_id_bytes = session_id.encode('utf-8')
            sess_id_len_bytes = struct.pack('!I', len(sess_id_bytes))
            meta_len_bytes = struct.pack('!I', len(json_bytes))
            
            packet = header + event_bytes + sess_id_len_bytes + sess_id_bytes + meta_len_bytes + json_bytes
            await self.websocket.send(packet)
            logging.info(f"[TTS-Stream] Sent StartSession (SessionID: {session_id[:8]})")

            # --- Send TaskRequest (Text) ---
            task_payload = {"req_params": {"text": text}}
            task_json = json.dumps(task_payload).encode('utf-8')
            
            header_task = self._pack_header(MSG_FULL_CLIENT_REQUEST, 0b0100, SER_JSON, COMP_NONE)
            event_task = struct.pack('!I', EVENT_TASK_REQUEST)
            task_len_bytes = struct.pack('!I', len(task_json))
            
            packet_task = header_task + event_task + sess_id_len_bytes + sess_id_bytes + task_len_bytes + task_json
            await self.websocket.send(packet_task)

            # --- Receive Loop ---
            while True:
                try:
                    resp = await self.websocket.recv()
                    msg_type, flags, body = self._parse_header(resp)
                    
                    logging.debug(f"[TTS-Stream] Recv Packet: Type={msg_type} Len={len(body)}")

                    # Audio Only Response
                    if msg_type == MSG_AUDIO_ONLY_RESPONSE:
                        offset = 0
                        if len(body) < 4: continue
                        s_len = struct.unpack('!I', body[offset:offset+4])[0]
                        offset += 4 + s_len
                        if len(body) < offset + 4: continue
                        a_len = struct.unpack('!I', body[offset:offset+4])[0]
                        offset += 4
                        audio_chunk = body[offset:offset+a_len]
                        
                        if audio_chunk:
                            logging.debug(f"[TTS-Stream] Yielding Audio Chunk {len(audio_chunk)} bytes")
                            yield audio_chunk 
                            
                    # Events
                    elif msg_type == MSG_FULL_SERVER_RESPONSE:
                        event_type = struct.unpack('!I', body[:4])[0]
                        logging.debug(f"[TTS-Stream] Event Type: {event_type}")
                        
                        if event_type == EVENT_SESSION_FINISHED:
                            logging.info("[TTS-Stream] Session Finished for %s", session_id[:8])
                            break # Done
                        elif event_type == EVENT_SESSION_FAILED:
                            # Parse Error from body
                            error_json = "{}"
                            try:
                                offset = 4
                                s_id_len = struct.unpack('!I', body[offset:offset+4])[0]
                                offset += 4 + s_id_len
                                p_len = struct.unpack('!I', body[offset:offset+4])[0]
                                offset += 4
                                error_json = body[offset:offset+p_len].decode('utf-8')
                            except: pass
                            logging.error(f"[TTS-Stream] SessionFailed for {session_id[:8]}: {error_json}")
                            break
                        elif event_type == EVENT_TTS_RESPONSE:
                            offset = 4
                            s_len = struct.unpack('!I', body[offset:offset+4])[0]
                            offset += 4 + s_len
                            a_len = struct.unpack('!I', body[offset:offset+4])[0]
                            offset += 4
                            audio_chunk = body[offset:offset+a_len]
                            if audio_chunk:
                                 yield audio_chunk
                    
                    elif msg_type == MSG_ERROR_RESPONSE:
                        # Decode Error Body
                        try:
                            # Usually JSON string
                            err_msg = body.decode('utf-8', errors='ignore')
                            logging.error(f"[TTS-Stream] Protocol Error (Type 15) for {session_id[:8]}: {err_msg}")
                        except:
                            logging.error(f"[TTS-Stream] Protocol Error (Type 15) for {session_id[:8]}: (Binary Data)")
                        break
                                 
                except Exception as e:
                    logging.error(f"[TTS-Stream] Recv Error: {e}")
                    self.connected = False
                    break
                             

    def _parse_header(self, data):
        # Returns msg_type, flags, body_bytes
        if len(data) < 4: return 0, 0, b""
        
        b0, b1, b2, b3 = struct.unpack('!BBBB', data[:4])
        # b0: Version(4) | HeaderSize(4)
        header_size = (b0 & 0x0F) * 4 # Usually 4
        msg_type = b1 >> 4
        flags = b1 & 0x0F
        
        # Compression?
        comp = b2 & 0x0F
        
        body = data[header_size:]
        if comp == COMP_GZIP:
             try:
                 body = gzip.decompress(body)
             except: pass 
             
        return msg_type, flags, body

    # === Bidirectional Streaming Methods ===
    
    async def _send_start_session_bidirection(self, session_id):
        """Start a bidirectional TTS session"""
        if not self.connected:
            await self.connect()
        
        req_params = {
            "speaker": "zh_female_tianmeixiaoyuan",  # TTS 2.0 compatible speaker
            "audio_params": {
                "format": "ogg_opus",
                "sample_rate": 24000
            }
        }
        
        meta_payload = {
            "user": {"uid": "user_backend"},
            "event": 100,
            "req_params": req_params
        }
        json_bytes = json.dumps(meta_payload).encode('utf-8')
        
        header = self._pack_header(MSG_FULL_CLIENT_REQUEST, 0b0100, SER_JSON, COMP_NONE)
        event_bytes = struct.pack('!I', EVENT_START_SESSION)
        sess_id_bytes = session_id.encode('utf-8')
        sess_id_len_bytes = struct.pack('!I', len(sess_id_bytes))
        meta_len_bytes = struct.pack('!I', len(json_bytes))
        
        packet = header + event_bytes + sess_id_len_bytes + sess_id_bytes + meta_len_bytes + json_bytes
        await self.websocket.send(packet)
        logging.info(f"[TTS Bidirection] Sent StartSession: {session_id[:8]}")
    
    async def _send_text_chunk(self, session_id, text):
        """Send a text chunk to TTS (TaskRequest)"""
        task_payload = {"req_params": {"text": text}}
        task_json = json.dumps(task_payload).encode('utf-8')
        
        header_task = self._pack_header(MSG_FULL_CLIENT_REQUEST, 0b0100, SER_JSON, COMP_NONE)
        event_task = struct.pack('!I', EVENT_TASK_REQUEST)
        sess_id_bytes = session_id.encode('utf-8')
        sess_id_len_bytes = struct.pack('!I', len(sess_id_bytes))
        task_len_bytes = struct.pack('!I', len(task_json))
        
        packet_task = header_task + event_task + sess_id_len_bytes + sess_id_bytes + task_len_bytes + task_json
        await self.websocket.send(packet_task)
        logging.debug(f"[TTS Bidirection] Sent TaskRequest: {text[:20]}...")
    
    async def _send_finish_session(self, session_id):
        """Finish the bidirectional TTS session"""
        header = self._pack_header(MSG_FULL_CLIENT_REQUEST, 0b0100, SER_JSON, COMP_NONE)
        event_bytes = struct.pack('!I', EVENT_FINISH_SESSION)
        sess_id_bytes = session_id.encode('utf-8')
        sess_id_len_bytes = struct.pack('!I', len(sess_id_bytes))
        payload_bytes = b'{}'
        payload_len_bytes = struct.pack('!I', len(payload_bytes))
        
        packet = header + event_bytes + sess_id_len_bytes + sess_id_bytes + payload_len_bytes + payload_bytes
        await self.websocket.send(packet)
        logging.info(f"[TTS Bidirection] Sent FinishSession: {session_id[:8]}")
    
    async def _receive_audio_stream(self, session_id):
        """Receive audio stream from TTS (async generator)"""
        while True:
            try:
                resp = await self.websocket.recv()
                msg_type, flags, body = self._parse_header(resp)
                
                # Audio Only Response
                if msg_type == MSG_AUDIO_ONLY_RESPONSE:
                    offset = 0
                    if len(body) < 4:
                        continue
                    s_len = struct.unpack('!I', body[offset:offset+4])[0]
                    offset += 4 + s_len
                    
                    if len(body) < offset + 4:
                        continue
                    a_len = struct.unpack('!I', body[offset:offset+4])[0]
                    offset += 4
                    audio_chunk = body[offset:offset+a_len]
                    if audio_chunk:
                        yield audio_chunk
                
                # Full Server Response with Event
                elif msg_type == MSG_FULL_SERVER_RESPONSE:
                    offset = 0
                    if len(body) < 4:
                        continue
                    event_num = struct.unpack('!I', body[offset:offset+4])[0]
                    offset += 4
                    
                    # SessionFinished - stop receiving
                    if event_num == EVENT_SESSION_FINISHED:
                        logging.info(f"[TTS Bidirection] SessionFinished received: {session_id[:8]}")
                        break
                    
                    # TTSResponse with audio
                    elif event_num == EVENT_TTS_RESPONSE:
                        if len(body) < offset + 4:
                            continue
                        s_len = struct.unpack('!I', body[offset:offset+4])[0]
                        offset += 4 + s_len
                        
                        if len(body) < offset + 4:
                            continue
                        payload_len = struct.unpack('!I', body[offset:offset+4])[0]
                        offset += 4
                        
                        if payload_len > 0 and len(body) >= offset + payload_len:
                            try:
                                payload_json = json.loads(body[offset:offset+payload_len].decode('utf-8'))
                                if 'data' in payload_json:
                                    audio_data = base64.b64decode(payload_json['data'])
                                    if audio_data:
                                        yield audio_data
                            except:
                                pass
                
                elif msg_type == MSG_ERROR_RESPONSE:
                    err_msg = body.decode('utf-8', errors='ignore')
                    logging.error(f"[TTS Bidirection] Error: {err_msg}")
                    break
                    
            except Exception as e:
                logging.error(f"[TTS Bidirection] Receive error: {e}")
                break
