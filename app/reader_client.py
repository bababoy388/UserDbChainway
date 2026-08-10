import asyncio
import httpx
import json
from sqlalchemy.orm import Session
from app import config, crud, state
from app.database import SessionLocal

async def poll_reader():
    """Фоновый цикл опроса считывателя (инвентаризация)."""
    async with httpx.AsyncClient(timeout=5.0) as client:
        # 1. Запускаем инвентаризацию
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

        # 2. Цикл опроса
        while not state.state.stop_requested:
            try:
                # Опрос: POST с пустым телом
                poll_resp = await client.post(
                    config.READER_BASE_URL + config.READER_POLL_URL,
                    headers={"Content-Type": "application/x-www-form-urlencoded"}
                )
                if poll_resp.status_code == 200:
                    data = poll_resp.json()
                    tags = data.get("data", [])
                    if tags:
                        for tag in tags:
                            epc = tag.get("epcHex")
                            if epc:
                                await process_tag(epc)
                else:
                    print(f"Ошибка опроса: {poll_resp.status_code}")
            except httpx.TimeoutException:
                pass
            except Exception as e:
                print(f"Ошибка в цикле опроса: {e}")
                await asyncio.sleep(1)

            await asyncio.sleep(config.POLL_INTERVAL)

        # 3. Остановка инвентаризации
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

async def process_tag(epc: str):
    """Проверяет EPC в БД и логирует результат."""
    db: Session = SessionLocal()
    try:
        ore = crud.get_ore_by_epc(db, epc)
        if ore:
            print(f"[{epc}] Найдена руда: {ore.ore_name} (категория: {ore.ore_category})")
        else:
            print(f"[{epc}] Неизвестная метка")
    finally:
        db.close()