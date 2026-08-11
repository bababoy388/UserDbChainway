import asyncio
import websockets

async def listen():
    uri = "ws://127.0.0.1:8001/ws"
    async with websockets.connect(uri) as websocket:
        print("Подключено к WebSocket")
        async for message in websocket:
            print("Получено:", message)

asyncio.run(listen())