# app/bot/manager.py — улучшенная стабильная версия 2025
import logging
import asyncio
from aiogram import Bot, Dispatcher
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.services.regos_client import RegosClient
from app.core.config import settings
from app.bot.handlers import router

logger = logging.getLogger(__name__)


class BotManager:
    def __init__(self):
        self.bots: dict[str, dict] = {}
        self._lock = asyncio.Lock()

    async def ensure(self, account):
        """
        Гарантирует, что бот для данного аккаунта создан и работает.
        Создаёт только один экземпляр на conn_id.
        """
        conn_id = account.connected_integration_id

        async with self._lock:
            # Бот уже создан → возвращаем существующий runtime
            runtime = self.bots.get(conn_id)
            if runtime:
                return runtime

            if not account.bot_token or not account.integration_url:
                logger.warning(f"Нет токена или URL для интеграции {conn_id}")
                return None

            # ✨ создаём отдельную aiohttp-сессию для каждого бота
            bot_session = AiohttpSession()
            bot_session._close_on_exit = True

            bot = Bot(
                token=account.bot_token,
                session=bot_session,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML),
            )

            # REST-клиент для Regos API
            regos = RegosClient(account.integration_url)
            bot.client = regos

            # Aiogram dispatcher
            dp = Dispatcher(storage=MemoryStorage())
            dp.include_router(router)

            webhook_url = f"{settings.service_base_url.rstrip('/')}/webhook/{conn_id}"

            # Устанавливаем webhook корректно
            try:
                await bot.set_webhook(
                    url=webhook_url,
                    secret_token=conn_id,
                    drop_pending_updates=True
                )
                logger.info(f"Webhook установлен для {conn_id}: {webhook_url}")
            except Exception as e:
                logger.error(f"Ошибка установки webhook для {conn_id}: {e}")
                await bot.session.close()
                return None

            # Сохраняем runtime
            runtime = {"bot": bot, "dp": dp}
            self.bots[conn_id] = runtime

            logger.info(f"Бот успешно запущен: {conn_id}")
            return runtime

    def get_runtime(self, conn_id: str):
        """Получить runtime бота, если он существует."""
        return self.bots.get(conn_id)

    async def shutdown(self):
        """
        Корректно выключаем всех ботов:
        - удаляем webhook
        - закрываем aiohttp session
        - закрываем httpx-клиент regos
        """
        logger.info("Останавливаем все боты...")

        for conn_id, runtime in list(self.bots.items()):
            bot = runtime["bot"]

            # Удаляем webhook
            try:
                await bot.delete_webhook(drop_pending_updates=True)
            except Exception as e:
                logger.warning(f"Ошибка удаления webhook {conn_id}: {e}")

            # Закрываем httpx клиент Regos
            try:
                if hasattr(bot, "client"):
                    await bot.client.close()
            except Exception as e:
                logger.warning(f"Ошибка закрытия RegosClient {conn_id}: {e}")

            # Закрываем aiohttp сессию
            try:
                await bot.session.close()
            except Exception as e:
                logger.warning(f"Ошибка закрытия сессии {conn_id}: {e}")

            logger.info(f"Бот остановлен: {conn_id}")

        self.bots.clear()


bot_manager = BotManager()
