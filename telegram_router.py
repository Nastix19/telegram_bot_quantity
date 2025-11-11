# telegram_router.py

from fastapi import APIRouter, Request, Header, HTTPException
from typing import Optional
from database import get_bot_token
from aiogram import Bot, Dispatcher
from aiogram.types import Update as TelegramUpdate
import logging

from handlers import start, stock
from config import REGOS_BASE_URL

router = APIRouter()
logger = logging.getLogger("telegram_router")

# Aiogram dispatcher (общий)
dispatcher = Dispatcher()
dispatcher.include_router(start.router)
dispatcher.include_router(stock.router)

@router.post("/webhook")
async def telegram_webhook(
    request: Request,
    x_telegram_secret: Optional[str] = Header(None, alias="X-Telegram-Bot-Api-Secret-Token")
):
    """
    Обработка вебхука Telegram для конкретного connected_integration_id
    """

    if not x_telegram_secret:
        raise HTTPException(status_code=400, detail="Missing secret token header")

    connected_integration_id = x_telegram_secret
    token = get_bot_token(connected_integration_id)
    if not token:
        logger.warning(f"No token for connected_integration_id={connected_integration_id}")
        raise HTTPException(status_code=404, detail="Bot token not found for this integration")

    # Формируем base_url REGOS для этого клиента
    regos_base = f"{REGOS_BASE_URL}/gateway/out/{connected_integration_id}/v1"

    # Устанавливаем клиента для stock handler
    stock.set_client(regos_base)

    # Получаем payload обновления от Telegram
    payload = await request.json()
    try:
        update = TelegramUpdate.model_validate(payload)
    except Exception as e:
        logger.exception("Invalid Telegram update payload")
        raise HTTPException(status_code=400, detail="Invalid update payload")

    bot = Bot(token=token)
    try:
        # Можно один раз установить команды бота
        try:
            await start.set_bot_commands(bot)
        except Exception:
            logger.debug("set_bot_commands skipped")

        await dispatcher.feed_update(bot, update)
    except Exception as e:
        logger.exception(f"Error processing update for cid={connected_integration_id}: {e}")
        raise HTTPException(status_code=500, detail="Failed to process update")
    finally:
        await bot.close()

    return {"ok": True}
