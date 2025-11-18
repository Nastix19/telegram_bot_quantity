from fastapi import APIRouter, Request, Header, HTTPException
from database import get_bot_token
from aiogram import Bot, Dispatcher
from aiogram.types import Update as TelegramUpdate
import logging

from handlers.start import router as start_router, set_bot_commands
from handlers.stock import router as stock_router, set_client  # только set_client

from config import REGOS_BASE_URL

router = APIRouter(prefix="/telegram")
logger = logging.getLogger("telegram_router")


dispatcher = Dispatcher()
dispatcher.include_router(start_router)
dispatcher.include_router(stock_router)


@router.post("/webhook/{connected_integration_id}")
async def telegram_webhook(
    connected_integration_id: str,
    request: Request,
    x_telegram_secret: str = Header(..., alias="X-Telegram-Bot-Api-Secret-Token")
):
    try:
        # 1. Проверяем секрет
        if x_telegram_secret != connected_integration_id:
            logger.warning("Invalid secret")
            raise HTTPException(status_code=403, detail="Invalid secret token")

        # 2. Получаем токен
        token = get_bot_token(connected_integration_id)
        if not token:
            raise HTTPException(status_code=404, detail="Bot token not found")

        # 3. Инициализируем RegosClient глобально
        base_url = f"{REGOS_BASE_URL}/gateway/out/{connected_integration_id}/v1"
        set_client(base_url)

        # 4. Парсим update
        data = await request.json()
        update = TelegramUpdate.model_validate(data)

        bot = Bot(token=token)

        # 5. Гарантируем, что команды установлены
        await set_bot_commands(bot)

        # 6. Передаем апдейт Aiogram
        await dispatcher.feed_update(bot, update)

        return {"ok": True}

    except Exception as e:
        logger.exception(f"TELEGRAM ERROR: {e}")
        return {"ok": False, "error": str(e)}
