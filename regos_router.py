# regos_router.py

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from database import save_integration
from utils import set_telegram_webhook

router = APIRouter(prefix="/regos")

class ConnectRequest(BaseModel):
    connected_integration_id: str
    bot_token: str

@router.post("/connect")
async def connect(data: ConnectRequest):
    save_integration(
        connected_integration_id=data.connected_integration_id,
        bot_token=data.bot_token
    )
    await set_telegram_webhook(
        bot_token=data.bot_token,
        connected_integration_id=data.connected_integration_id,
    )
    return {"status": "success"}
