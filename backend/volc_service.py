import os
import json
import uuid
import gzip
import time
import requests
import websockets
import asyncio
from dotenv import load_dotenv

load_dotenv()

# Configuration
APPID = os.getenv("VOLC_APPID")
ACCESS_TOKEN = os.getenv("VOLC_ACCESS_KEY") # This might be named differently in env/code
# Actually Volcengine usually uses Access Key / Secret Key for signature, 
# OR a Token for specific services. For WebSocket ASR, we usually need custom headers with signature. 
# However, simpler implementation might use the Token if supported, but typically it is AK/SK.
# Let's check if the user provided AK/SK. Yes.
VOLC_AK = os.getenv("VOLC_ACCESS_KEY")
VOLC_SK = os.getenv("VOLC_SECRET_KEY")
ASR_CLUSTER = os.getenv("VOLC_ASR_CLUSTER")
TTS_CLUSTER = os.getenv("VOLC_TTS_CLUSTER")

# --- Volcengine ASR Protocol V2 Constants ---
PROTOCOL_VERSION = 0b0001
HEADER_SIZE = 0b0001
MSG_TYPE_FULL_CLIENT_REQUEST = 0b0001
MSG_TYPE_AUDIO_ONLY_REQUEST = 0b0010
MSG_TYPE_FULL_SERVER_RESPONSE = 0b1001
MSG_TYPE_ERROR = 0b1111
SERIALIZATION_JSON = 0b0001
SERIALIZATION_NONE = 0b0000
COMPRESSION_GZIP = 0b0001
COMPRESSION_NONE = 0b0000

def construct_protocol_packet(msg_type, payload_bytes, serialization_method=SERIALIZATION_NONE, compression_method=COMPRESSION_NONE, is_last_packet=False):
    """
    Constructs a Volcengine ASR Protocol V2 Packet.
    Header (4 bytes): [Ver|HeadSz] [MsgType|Flags] [Serial|Comp] [Reserved]
    Payload Size (4 bytes): Big-endian unsigned int
    Payload: Data (Compressed if needed)
    """
    # 1. Compress Payload
    if compression_method == COMPRESSION_GZIP:
        payload_bytes = gzip.compress(payload_bytes)
        
    # 2. Build Header
    # Byte 0: Version (4) | Header Size (4)
    byte_0 = (PROTOCOL_VERSION << 4) | HEADER_SIZE
    
    # Byte 1: Msg Type (4) | Flags (4)
    flags = 0b0000
    if is_last_packet and msg_type == MSG_TYPE_AUDIO_ONLY_REQUEST:
        flags = 0b0010
    byte_1 = (msg_type << 4) | flags
    
    # Byte 2: Serialization (4) | Compression (4)
    byte_2 = (serialization_method << 4) | compression_method
    
    # Byte 3: Reserved
    byte_3 = 0x00
    
    header = struct.pack('!BBBB', byte_0, byte_1, byte_2, byte_3)
    
    # 3. Payload Size (4 bytes big-endian)
    payload_size = struct.pack('!I', len(payload_bytes))
    
    return header + payload_size + payload_bytes

def parse_protocol_packet(packet_data):
    """
    Parses a Volcengine ASR Protocol V2 Packet.
    Returns: (msg_type, payload_bytes, is_gzip)
    """
    if len(packet_data) < 8:
        return None, None, False
        
    header = packet_data[:4]
    b0, b1, b2, b3 = struct.unpack('!BBBB', header)
    
    msg_type = b1 >> 4
    compression_method = b2 & 0b00001111
    
    payload_struct = packet_data[4:8]
    payload_len = struct.unpack('!I', payload_struct)[0]
    
    payload = packet_data[8:8+payload_len]
    
    is_gzip = (compression_method == COMPRESSION_GZIP)
    
    return msg_type, payload, is_gzip

ASR_URL = "wss://openspeech.bytedance.com/api/v2/asr"
TTS_URL = "https://openspeech.bytedance.com/api/v1/tts"

# Helper for signatures might be complex. 
# SIMPLIFICATION: We will try to use the 'volcengine-python-sdk' if available for TTS, 
# but for WebSocket ASR, we often need to construct the JSON payload manually.

# ASR: We will implement a simple client that sends audio and receives text.
# NOTE: This effectively acts as a proxy.
import struct
import io

from fastapi import WebSocket
from volcenginesdkcore.signv4 import SignerV4

async def asr_stream(client_ws: WebSocket):
    # Load Credentials
    ak = os.getenv("VOLC_ACCESS_KEY")
    sk = os.getenv("VOLC_SECRET_KEY")
    appid = os.getenv("VOLC_APPID")
    cluster = os.getenv("VOLC_ASR_CLUSTER")
    
    if not all([ak, sk, appid, cluster]):
        print("Error: Missing Volcengine Config")
        await client_ws.close()
        return

    # 1. Sign Request (ASR V2)
    # The V2 endpoint is wss://openspeech.bytedance.com/api/v2/asr
    
    method = "GET"
    service = "asr"
    region = "cn-north-1"
    host = "openspeech.bytedance.com"
    path = "/api/v2/asr" 
    
    # Create Signer
    url = f"wss://{host}{path}"
    headers = {
        "Host": host,
        "X-Api-Resource-Id": "volc.asr.sauc.realtime" # Required for some ASR services
    }
    
    query = {
        "appid": appid,
        "cluster": cluster
    }
    
    # ASR Config Payload (Full Client Request)
    req_id = str(uuid.uuid4())
    init_payload = {
        "app": {
            "appid": appid,
            "token": "access_token", 
            "cluster": cluster
        },
        "user": {
            "uid": "user_test"
        },
        "audio": {
            "format": "mp3",
            "rate": 16000,
            "bits": 16,
            "channel": 1,
            "codec": "mp3"
        },
        "request": {
            "reqid": req_id,
            "workflow": "audio_in,resample,partition,vad,gpu_inference,transformer,punctuation_restoration,itn",
            "result_type": "full",
            "sequence": 1
        }
    }

    # Sign
    signer = SignerV4()
    try:
        signer.sign(path, method, headers, "", None, query, ak, sk, region, service)
        print("Signed Headers:", headers)
    except Exception as e:
        print(f"Signing Failed: {e}")
        await client_ws.close()
        return

    # Merge query params into URL
    if query:
        import urllib.parse
        url += "?" + urllib.parse.urlencode(query)

    # REMOVE Host from headers passed to websockets
    ws_headers = headers.copy()
    if "Host" in ws_headers:
        del ws_headers["Host"]

    try:
        # Disable SSL Verify for WebSocket (Workaround)
        import ssl
        ssl_context = ssl.create_default_context()
        ssl_context.check_hostname = False
        ssl_context.verify_mode = ssl.CERT_NONE
        
        async with websockets.connect(url, additional_headers=ws_headers, ssl=ssl_context) as volc_ws:
            print("Connected to Volcengine ASR")
            
            # --- Send 1: Full Client Request (Init) ---
            init_json_str = json.dumps(init_payload)
            init_json_bytes = init_json_str.encode('utf-8')
            
            # Pack using Protocol V2 (MsgType=1, Serial=JSON, Comp=Gzip)
            init_packet = construct_protocol_packet(
                MSG_TYPE_FULL_CLIENT_REQUEST, 
                init_json_bytes, 
                SERIALIZATION_JSON, 
                COMPRESSION_GZIP
            )
            
            await volc_ws.send(init_packet)
            print("Sent Init Packet (Protocol V2, Gzipped)")

            print("Tasks defined. Starting Loop...")
            
            async def send_audio_loop():
                print("Send Audio Loop Started")
                try:
                    async for message in client_ws.iter_bytes():
                        if not message:
                            continue
                            
                        if isinstance(message, str):
                            message = message.encode('utf-8')
                        
                        # Pack Audio Chunk (MsgType=2, Serial=JSON, Comp=Gzip)
                        # MATCHING DEMO: The demo uses defaults: Serial=JSON (1), Comp=GZIP (1) even for audio.
                        audio_packet = construct_protocol_packet(
                            MSG_TYPE_AUDIO_ONLY_REQUEST,
                            message,
                            SERIALIZATION_JSON, 
                            COMPRESSION_GZIP
                        )

                        await volc_ws.send(audio_packet)
                        
                except Exception as e:
                    print(f"Client->Volc Error: {e}")
                finally:
                    print("Send Audio Loop Ended")

            async def receive_text_loop():
                print("Receive Text Loop Started")
                try:
                    async for message in volc_ws:
                        # 1. Parse Protocol Packet
                        msg_type, payload, is_gzip = parse_protocol_packet(message)
                        
                        if msg_type is None:
                            print("Received Invalid Packet Header")
                            continue
                            
                        if msg_type == MSG_TYPE_ERROR:
                            if is_gzip:
                                try:
                                    payload = gzip.decompress(payload)
                                except Exception as e:
                                    print(f"Error Payload Decompress Failed: {e}")
                            
                            code = int.from_bytes(payload[:4], 'big')
                            msg_len = int.from_bytes(payload[4:8], 'big')
                            error_msg = payload[8:8+msg_len].decode('utf-8', errors='ignore')
                            print(f"Volc Engine Error Code {code}: {error_msg}")
                            continue
                            
                        if msg_type == MSG_TYPE_FULL_SERVER_RESPONSE:
                            # 2. Decompress Payload
                            if is_gzip:
                                try:
                                    payload = gzip.decompress(payload)
                                except Exception as e:
                                    print(f"Gzip Decompress Failed: {e}")
                                    continue
                            
                            # 3. Parse JSON
                            try:
                                response = json.loads(payload.decode('utf-8'))
                                # print(f"Volc Response: {response}")
                                
                                if 'result' in response and len(response['result']) > 0:
                                    text = response['result'][0]['text']
                                    await client_ws.send_json({"text": text})
                                    
                            except json.JSONDecodeError:
                                print(f"JSON Parse Failed: {payload}")
                except Exception as e:
                    print(f"Volc->Client Error: {e}")
                finally:
                    print("Receive Text Loop Ended")

            # Run Both Loops
            await asyncio.gather(send_audio_loop(), receive_text_loop())

    except Exception as e:
        print(f"Volcengine Connection Error: {e}")
        await client_ws.send_json({"text": "(服务连接异常)"})
    
    print("ASR Stream Ended")

def synthesize_speech(text, output_dir="backend/static/audio"):
    """
    Synthesize speech using Volcengine TTS (HTTP API with Manual Signing).
    """
    import json
    import requests
    from volcenginesdkcore.signv4 import SignerV4

    os.makedirs(output_dir, exist_ok=True)
    filename = f"{uuid.uuid4()}.mp3"
    filepath = os.path.join(output_dir, filename)
    
    # Configuration
    host = "openspeech.bytedance.com"
    path = "/api/v1/tts"
    method = "POST"
    url = f"https://{host}{path}"
    
    # Headers - Let Signer Handle Host
    headers = {
        "Content-Type": "application/json"
    }
    
    # Body Payload
    req_id = str(uuid.uuid4())
    payload = {
        "app": {
            "appid": APPID,
            "token": "access_token", 
            "cluster": TTS_CLUSTER
        },
        "user": {
            "uid": "user_1"
        },
        "audio": {
            "voice_type": "BV701_streaming", 
            "encoding": "mp3",
            "speed": 10,
            "volume": 10,
            "pitch": 10
        },
        "request": {
            "reqid": req_id,
            "text": text,
            "text_type": "plain",
            "operation": "query"
        }
    }
    # Use compact separators AND sort_keys for signature consistency
    body = json.dumps(payload, separators=(',', ':'), sort_keys=True)
    
    # Sign
    signer = SignerV4()
    # Try 'tts' service name first, then 'speech' if fails. 
    # Mismatch often comes from incorrect service name in Credential scope.
    service = "tts"  
    region = "cn-north-1"
    
    try:
        # Signature: (path, method, headers, body, post_params, query, ak, sk, region, service, session_token=None)
        # IMPORTANT: signer.sign MUTATES the headers dict
        signer.sign(path, method, headers, body, {}, {}, VOLC_AK, VOLC_SK, region, service)
    except Exception as e:
        print(f"TTS Signing Failed: {e}")
        return None

    try:
        # Disable SSL Verify for requests as well
        resp = requests.post(url, headers=headers, data=body, verify=False)
        
        if resp.status_code == 200:
            resp_json = resp.json()
            if "data" in resp_json:
                import base64
                if resp_json.get("code") == 3000:
                    audio_data = base64.b64decode(resp_json["data"])
                    with open(filepath, "wb") as f:
                        f.write(audio_data)
                    return f"/static/audio/{filename}"
                else:
                    print(f"TTS API Error: {resp_json}")
            else:
                print(f"TTS Unexpected Response: {resp.text}")
        else:
            print(f"TTS HTTP Error {resp.status_code}: {resp.text}")
    except Exception as e:
        print(f"TTS Request Exception: {e}")
        
    return None
