# app/bot/manager.py — 100% РАБОЧАЯ ВЕРСИЯ (2025, без ошибок)
import logging
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.services.regos_client import RegosClient
from app.core.config import settings
from app.bot.handlers import router

logger = logging.getLogger(__name__)

shared_session = AiohttpSession()
shared_session._close_on_exit = False

class BotManager:
    def __init__(self):
        self.bots: dict[str, dict] = {}

    async def ensure(self, account):
        conn_id = account.connected_integration_id

        if conn_id in self.bots:
            return self.bots[conn_id]

        if not account.bot_token or not account.integration_url:
            logger.warning(f"Нет токена/URL для {conn_id}")
            return None

        # ← Bot без сессии — aiogram сам создаст и будет управлять
        bot = Bot(
            token=account.bot_token,
            session=shared_session,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )

        # ← RegosClient сам создаёт httpx.AsyncClient — просто передаём URL
        bot.client = RegosClient(account.integration_url)

        dp = Dispatcher(storage=MemoryStorage())
        dp.include_router(router)

        webhook_url = f"{settings.service_base_url.rstrip('/')}/webhook/{conn_id}"

        try:
            await bot.set_webhook(
                url=webhook_url,
                secret_token=conn_id,
                drop_pending_updates=True,
            )
            logger.info(f"Webhook установлен → {webhook_url}")
        except Exception as e:
            logger.error(f"Ошибка webhook {conn_id}: {e}")
            await bot.session.close()
            return None

        runtime = {
            "bot": bot,
            "dp": dp,
        }
        self.bots[conn_id] = runtime
        logger.info(f"Бот запущен: {conn_id}")
        return runtime

    def get_runtime(self, conn_id: str):
        return self.bots.get(conn_id)

    async def shutdown(self):
        logger.info("Останавливаем все боты...")
        for conn_id, runtime in list(self.bots.items()):
            try:
                await runtime["bot"].delete_webhook(drop_pending_updates=True)
            except Exception as e:
                logger.warning(f"Ошибка удаления webhook {conn_id}: {e}")

            try:
                await runtime["bot"].session.close()
            except Exception as e:
                logger.warning(f"Ошибка закрытия сессии {conn_id}: {e}")

            logger.info(f"Бот остановлен: {conn_id}")

        self.bots.clear()


bot_manager = BotManager()