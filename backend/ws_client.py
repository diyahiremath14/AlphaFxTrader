# ws_client.py
import asyncio
import websockets
import json

async def run():
    uri = "ws://127.0.0.1:8000/ws/prices"
    async with websockets.connect(uri) as ws:
        async def sender():
            while True:
                await ws.send("ping")    # server's receive_text() will unblock
                await asyncio.sleep(10)  # send ping every 10s

        async def receiver():
            while True:
                msg = await ws.recv()
                try:
                    data = json.loads(msg)
                    print("RECV:", data)
                except Exception:
                    print("RAW:", msg)

        await asyncio.gather(sender(), receiver())

if __name__ == "__main__":
    asyncio.run(run())
