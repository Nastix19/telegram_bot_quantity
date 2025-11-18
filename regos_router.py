from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from database import save_integration, get_bot_token
from utils import set_telegram_webhook
import logging

router = APIRouter(prefix="/regos")
logger = logging.getLogger("regos_router")

class RegosRequest(BaseModel):
    action: str
    connected_integration_id: str
    data: Optional[Dict[str, Any]] = None

@router.post("", status_code=200)
async def regos_entry(req: RegosRequest):
    action = req.action
    cid = req.connected_integration_id
    data = req.data or {}

    logger.info(f"REGOS → action={action}, cid={cid}, data={data}")


    # Connect

    if action == "Connect":
        date = data.get("date")
        if not date:
            raise HTTPException(status_code=400, detail="Missing date in Connect")
        # Создаём запись
        save_integration(cid, bot_token="")
        logger.info(f"Integration {cid} connected (token empty)")
        return {"status": "connected", "connected_integration_id": cid}


    # Disconnect

    if action == "Disconnect":
        date = data.get("date")
        if not date:
            raise HTTPException(status_code=400, detail="Missing date in Disconnect")
        # Удаляем/очищаем токен
        save_integration(cid, bot_token="")
        logger.info(f"Integration {cid} disconnected")
        return {"status": "disconnected", "connected_integration_id": cid}


    # Reconnect

    if action == "Reconnect":
        date = data.get("date")
        prev = data.get("previous_integration_id")
        if not date or not prev:
            raise HTTPException(status_code=400, detail="Missing fields in Reconnect")
        # Создаём новую запись (token придёт через UpdateSettings)
        save_integration(cid, bot_token="")
        logger.info(f"Integration {cid} reconnected (previous={prev})")
        return {"status": "reconnected", "connected_integration_id": cid}


    # UpdateSettings

    if action == "UpdateSettings":
        settings = data.get("settings", [])
        if not isinstance(settings, list):
            raise HTTPException(status_code=400, detail="settings must be a list")

        # Ищем настройку BOT_TOKEN (name_var == "BOT_TOKEN")
        bot_token = None
        for s in settings:
            if s.get("name_var") == "BOT_TOKEN":
                bot_token = s.get("value")
                break

        if bot_token:
            save_integration(cid, bot_token)
            logger.info(f"Saved bot token for {cid}, registering webhook")

            try:
                await set_telegram_webhook(bot_token, cid)
            except Exception as e:
                logger.exception(f"Failed to set webhook for {cid}: {e}")
                raise HTTPException(status_code=500, detail="Failed to set webhook")
            return {"status": "settings_updated", "connected_integration_id": cid}
        else:

            logger.info(f"No BOT_TOKEN in settings for {cid}, nothing to change")
            return {"status": "updated", "connected_integration_id": cid}


    raise HTTPException(status_code=400, detail=f"Unknown action '{action}'")
