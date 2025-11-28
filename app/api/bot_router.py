# app/api/bot_router.py
from fastapi import APIRouter, Request, Header, HTTPException
from app.bot.manager import bot_manager

router = APIRouter()

@router.post("/{conn_id}")
async def telegram_webhook(
    conn_id: str,
    request: Request,
    x_telegram_bot_api_secret_token: str | None = Header(default=None)
):
    # Проверка secret token (Telegram присылает его в заголовке)
    if x_telegram_bot_api_secret_token != conn_id:
        raise HTTPException(403, "Forbidden")

    # Получаем уже запущенный бот по conn_id
    runtime = bot_manager.bots.get(conn_id)
    if not runtime:
        raise HTTPException(404, "Bot not running")

    # Парсим и отправляем обновление в aiogram
    update_dict = await request.json()
    from aiogram.types import Update
    await runtime["dp"].feed_update(bot=runtime["bot"], update=Update(**update_dict))

    return {"ok": True}