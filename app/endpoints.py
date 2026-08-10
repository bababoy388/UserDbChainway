import json
import httpx
from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session

from app import crud, security, schemas, state, config
from app.database import SessionLocal
from app.reader_client import poll_reader
from app.dependencies import get_current_user, get_db


router = APIRouter()

@router.post("/login", response_model=schemas.Token)
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),  # ← правильная зависимость
    db: Session = Depends(get_db)                      # ← добавили аннотацию типа
):
    user = crud.authenticate_user(db, form_data.username, form_data.password)
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "Bearer"},
        )
    access_token = security.create_access_token(
        data={"sub": user.username, "admin": user.is_admin}
    )
    return {"access_token": access_token, "token_type": "bearer"}

@router.post("/start")
async def start_scan(background_tasks: BackgroundTasks, current_user = Depends(get_current_user)):
    if state.state.is_running:
        raise HTTPException(status_code=400, detail="Scanning already running")
    state.state.is_running = True
    state.state.stop_requested = False
    background_tasks.add_task(poll_reader)
    return {"status": "started"}

@router.post("/stop")
async def stop_scan(current_user = Depends(get_current_user)):
    if not state.state.is_running:
        raise HTTPException(status_code=400, detail="Scanning not running")
    state.state.stop_requested = True
    return {"status": "stopping"}

@router.get("/read_single")
async def read_single_tag(current_user = Depends(get_current_user)):
    """Считать одну метку (единичный режим)."""
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
                raise HTTPException(status_code=400, detail=f"Reader error: {result.get('message')}")

            epc_hex = result.get("hexTagData")
            if not epc_hex:
                return {"message": "No tag found"}

            db = SessionLocal()
            try:
                ore = crud.get_ore_by_epc(db, epc_hex)
                if ore:
                    return {"epc": epc_hex, "ore_name": ore.ore_name, "ore_category": ore.ore_category}
                else:
                    return {"epc": epc_hex, "ore_name": None, "message": "Unknown tag"}
            finally:
                db.close()

        except httpx.TimeoutException:
            raise HTTPException(status_code=504, detail="Reader timeout")
        except json.JSONDecodeError:
            raise HTTPException(status_code=500, detail="Invalid JSON response from reader")
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

@router.get("/status")
async def get_status(current_user = Depends(get_current_user)):
    return {"running": state.state.is_running}