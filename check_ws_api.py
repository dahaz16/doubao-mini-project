import asyncio
import websockets

async def check_api():
    try:
        async with websockets.connect("wss://echo.websocket.org") as ws:
            print(f"Object type: {type(ws)}")
            print(f"Attributes: {dir(ws)}")
            # Try some common ones
            for attr in ['open', 'closed', 'state']:
                try:
                    val = getattr(ws, attr)
                    print(f"Attribute '{attr}': {val}")
                except Exception as e:
                    print(f"Attribute '{attr}' failed: {e}")
    except Exception as e:
        print(f"Echo test failed (could be network): {e}")

if __name__ == "__main__":
    asyncio.run(check_api())
