import websockets.client
import asyncio
from websockets.extensions import permessage_deflate

# websockets 14+ used ClientConnection
print("Inspecting websockets.client properties:")
try:
    # We can try to instantiate without connecting or just dir the class
    print(f"Attributes in websockets.client: {dir(websockets.client)}")
    if hasattr(websockets.client, 'ClientConnection'):
        print(f"Attributes in ClientConnection: {dir(websockets.client.ClientConnection)}")
except Exception as e:
    print(f"Inspection failed: {e}")
