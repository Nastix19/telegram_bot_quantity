from fastapi import APIRouter, Request, Header, HTTPException
from app.bot.manager import bot_manager
from aiogram.types import Update

router = APIRouter()

@router.post("/{conn_id}")
async def webhook(conn_id: str, request: Request, x_telegram_bot_api_secret_token: str = Header(None)):
    if x_telegram_bot_api_secret_token != conn_id:
        raise HTTPException(403)

    runtime = bot_manager.get_runtime(conn_id)
    if not runtime:
        raise HTTPException(404)

    update = Update(**(await request.json()))
    await runtime["dp"].feed_update(runtime["bot"], update)

    return {"ok": True}
