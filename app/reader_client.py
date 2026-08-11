import asyncio
import httpx
import json
from datetime import datetime
from app import config, state
from app.websocket_manager import manager


async def poll_reader():
    """
    Фоновый опрос считывателя.
    Формирует JSON с данными меток, временем и количеством.
    """
    async with httpx.AsyncClient(timeout=5.0) as client:
        # Запуск инвентаризации
        start_payload = {
            "type": "Reader-startInventoryRequest",
            "tagFilter": {
                "tagMemoryBank": "epc",
                "bitOffset": 0,
                "bitLength": 0,
                "hexMask": None
            }
        }
        try:
            start_resp = await client.post(
                config.READER_BASE_URL + config.READER_START_URL,
                data={"data": json.dumps(start_payload)},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
            if start_resp.status_code != 200:
                print(f"Ошибка запуска: {start_resp.status_code} - {start_resp.text}")
                return
        except Exception as e:
            print(f"Ошибка при запуске: {e}")
            return

        # Цикл опроса
        while not state.state.stop_requested:
            try:
                poll_resp = await client.post(
                    config.READER_BASE_URL + config.READER_POLL_URL,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                if poll_resp.status_code == 200:
                    data = poll_resp.json()
                    tags = data.get("data", [])
                    count = len(tags)

                    result = {
                        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                        "tags": [
                            {
                                "epc": tag.get("epcHex"),
                                "signal": tag.get("rssi")
                            }
                            for tag in tags
                        ]
                    }

                    state.state.last_reader_data = result
                    await manager.broadcast(result)

                else:
                    print(f"Ошибка опроса: {poll_resp.status_code}")
            except httpx.TimeoutException:
                pass
            except Exception as e:
                print(f"Ошибка в цикле опроса: {e}")
                await asyncio.sleep(1)

            await asyncio.sleep(config.POLL_INTERVAL)

        # Остановка инвентаризации
        stop_payload = {"type": "Reader-stopInventoryRequest"}
        try:
            await client.post(
                config.READER_BASE_URL + config.READER_STOP_URL,
                data={"data": json.dumps(stop_payload)},
                headers={"Content-Type": "application/x-www-form-urlencoded"}
            )
        except:
            pass
        state.state.is_running = False