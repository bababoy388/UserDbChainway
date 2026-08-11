import json
from datetime import datetime
import httpx
from fastapi import APIRouter, BackgroundTasks, HTTPException
from starlette.websockets import WebSocket, WebSocketDisconnect

from app import state, config
from app.reader_client import poll_reader
from app.websocket_manager import manager

router = APIRouter()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await manager.connect(websocket)
    try:
        if state.state.last_reader_data:
            await websocket.send_json(state.state.last_reader_data)
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        manager.disconnect(websocket)

@router.get("/last_data")
async def get_last_reader_data():
    return state.state.last_reader_data or {"message": "No data yet"}

@router.post("/start")
async def start_scan(background_tasks: BackgroundTasks):
    """ Запуск инвентаризации """
    if state.state.is_running:
        raise HTTPException(status_code=400, detail="Scanning already running")
    state.state.is_running = True
    state.state.stop_requested = False
    background_tasks.add_task(poll_reader)
    return {"status": "started"}

@router.post("/stop")
async def stop_scan():
    """ Остановка инвентаризации """
    if not state.state.is_running:
        raise HTTPException(status_code=400, detail="Scanning not running")
    state.state.stop_requested = True
    return {"status": "stopping"}

@router.get("/status")
async def get_status():
    """ Статус активности инвентаризации """
    return {"running": state.state.is_running}

@router.get("/read_single")
async def read_single_tag():
    """ Считать одну метку (единичный режим) """
    async with httpx.AsyncClient(timeout=5.0) as client:
        data_payload = {
            "type": "Reader-tagReadRequest",
            "tagParameters": {
                "hexAccessPassword": "00000000",
                "tagMemoryBank": "epc",
                "wordOffset": 2,
                "wordLength": 6
            }
        }
        try:
            response = await client.post(
                config.READER_BASE_URL + config.READER_SINGLE_URL,
                data={"data": json.dumps(data_payload)},
                headers={
                    "Content-Type": "application/x-www-form-urlencoded",
                    "Accept": "application/json",
                    "X-Requested-With": "XMLHttpRequest"
                }
            )
            if response.status_code != 200:
                raise HTTPException(status_code=response.status_code, detail="Reader error")

            result = response.json()

            if result.get("code") != 0:
                return {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "epc": None,
                    "message": f"Reader error: {result.get('message', 'Unknown error')}",
                    "code": result.get("code")
                }

            epc_hex = result.get("hexTagData")
            if not epc_hex:
                return {
                    "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                    "epc": None,
                    "message": "No tag found (empty EPC)"
                }

            return {
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M"),
                "epc": epc_hex,
            }

        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Reader timeout")
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="Invalid JSON response from reader")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))
