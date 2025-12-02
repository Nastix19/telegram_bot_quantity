# app/bot/manager.py — стабильная версия с ensure для совместимости
import logging
import asyncio
from aiogram import Bot, Dispatcher, Router
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.session.aiohttp import AiohttpSession
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from app.services.regos_client import RegosClient
from app.core.config import settings
from app.bot.handlers import router

logger = logging.getLogger(__name__)


def _clone_router(source: Router) -> Router:
    """Создаёт независимую копию router для каждого Dispatcher."""
    cloned = Router(name=source.name)
    for observer_name, observer in source.observers.items():
        target_observer = getattr(cloned, observer_name, None)
        if target_observer is None:
            continue
        for handler in observer.handlers:
            filters = [f.callback for f in handler.filters] if handler.filters else []
            flags = handler.flags.copy() if handler.flags else {}
            target_observer.register(handler.callback, *filters, flags=flags)
        for middleware in getattr(observer, "middlewares", []) or []:
            target_observer.middleware(middleware.handler)
    for sub_router in getattr(source, "sub_routers", []):
        cloned.include_router(_clone_router(sub_router))
    error_handlers = getattr(source.errors, "handlers", [])
    for handler in error_handlers:
        filters = [f.callback for f in handler.filters] if handler.filters else []
        flags = handler.flags.copy() if handler.flags else {}
        cloned.errors.register(handler.callback, *filters, flags=flags)
    return cloned


class BotManager:
    def __init__(self):
        self.bots: dict[str, dict] = {}
        self._lock = asyncio.Lock()


    async def ensure_runtime(self, account):
        conn_id = account.connected_integration_id

        async with self._lock:
            runtime = self.bots.get(conn_id)
            if runtime:
                return runtime

            if not account.bot_token or not account.integration_url:
                logger.warning(f"Нет токена или URL для интеграции {conn_id}")
                return None

            bot_session = AiohttpSession()
            bot_session._close_on_exit = True

            bot = Bot(
                token=account.bot_token,
                session=bot_session,
                default=DefaultBotProperties(parse_mode=ParseMode.HTML),
            )

            from aiogram.types import BotCommand

            try:
                await bot.set_my_commands([
                    BotCommand(command="start", description="Старт бота"),
                    BotCommand(command="stock", description="Поиск товара"),
                    BotCommand(command="minimum", description="Минимальные остатки")
                ])
                logger.info(f"Команды установлены для {conn_id}")
            except Exception as e:
                logger.error(f"Ошибка установки команд меню для {conn_id}: {e}")


            regos = RegosClient(account.integration_url)
            bot.client = regos


            dp = Dispatcher(storage=MemoryStorage())
            dp.include_router(_clone_router(router))

            webhook_url = f"{settings.service_base_url.rstrip('/')}/webhook/{conn_id}"


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


            runtime = {"bot": bot, "dp": dp}
            self.bots[conn_id] = runtime

            logger.info(f"Бот успешно запущен: {conn_id}")
            return runtime


    async def ensure(self, account):
        return await self.ensure_runtime(account)

    def get_runtime(self, conn_id: str):
        return self.bots.get(conn_id)

    async def shutdown(self):
        logger.info("Останавливаем все боты...")
        for conn_id, runtime in list(self.bots.items()):
            bot = runtime["bot"]


            try:
                await bot.delete_webhook(drop_pending_updates=True)
            except Exception as e:
                logger.warning(f"Ошибка удаления webhook {conn_id}: {e}")


            try:
                if hasattr(bot, "client"):
                    await bot.client.close()
            except Exception as e:
                logger.warning(f"Ошибка закрытия RegosClient {conn_id}: {e}")


            try:
                await bot.session.close()
            except Exception as e:
                logger.warning(f"Ошибка закрытия сессии {conn_id}: {e}")

            logger.info(f"Бот остановлен: {conn_id}")

        self.bots.clear()


bot_manager = BotManager()
