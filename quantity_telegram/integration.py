from typing import Dict, List, Optional

from aiogram import Bot, Dispatcher, types
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

from schemas.integration.telegram_integration_base import IntegrationTelegramBase
from schemas.integration.base import (
    IntegrationSuccessResponse,
    IntegrationErrorResponse,
    IntegrationErrorModel,
)
from core.logger import setup_logger
from utils.telegram import extract_chat_id

logger = setup_logger("quantity_bot")


class QuantityTelegramIntegration(IntegrationTelegramBase):
    def __init__(self):
        super().__init__()
        self.bot: Optional[Bot] = None
        self.dp: Optional[Dispatcher] = None
        self._handlers_ready = False

    # ==================== INIT ====================

    async def _initialize_bot(self):
        if self.bot:
            return

        settings_map = await self._fetch_settings()

        bot_token = settings_map.get("bot_token")
        if not bot_token:
            raise ValueError("BOT_TOKEN не указан в настройках интеграции")

        self.bot = Bot(
            token=bot_token,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML),
        )

        self.dp = Dispatcher(storage=MemoryStorage())

        # Пробрасываем методы REGOS API в bot
        self.bot.get_items = self.get_items
        self.bot.get_stocks = self.get_stocks
        self.bot.get_current_quantity = self.get_current_quantity

        self._setup_handlers()

    def _setup_handlers(self):
        if self._handlers_ready:
            return
        from .handlers.quantity import router
        self.dp.include_router(router)
        self._handlers_ready = True

    # ==================== REGOS API ====================

    async def get_items(self) -> List[Dict]:
        async with self.regos_api as api:
            resp = await api.item.get(limit=1000)
            return resp.result or []

    async def get_stocks(self) -> List[Dict]:
        async with self.regos_api as api:
            resp = await api.stock.get(limit=1000)
            return resp.result or []

    async def get_current_quantity(
        self, item_ids: List[int], stock_ids: List[int]
    ) -> Dict:
        result: Dict[int, Dict[int, int]] = {}

        async with self.regos_api as api:
            for i in range(0, len(item_ids), 250):
                batch = item_ids[i : i + 250]
                resp = await api.item.get_current_quantity(
                    item_ids=batch,
                    stock_ids=stock_ids,
                )
                for e in resp.result or []:
                    item_id = e.get("item_id")
                    stock_id = e.get("stock_id")
                    qty = e.get("quantity")
                    if item_id is not None and stock_id is not None:
                        result.setdefault(item_id, {})[stock_id] = qty

        return result

    # ==================== LIFECYCLE ====================

    async def connect(self, **kwargs) -> Dict:
        await self._initialize_bot()

        webhook_url = (
            f"{self.config.external_base_url}/"
            f"{self.connected_integration_id}/external/"
        )

        await self.bot.set_webhook(
            url=webhook_url,
            drop_pending_updates=True,
        )

        logger.info(f"Webhook установлен: {webhook_url}")
        return {"status": "connected", "webhook_url": webhook_url}

    async def disconnect(self, **kwargs) -> Dict:
        if self.bot:
            try:
                await self.bot.delete_webhook(drop_pending_updates=True)
            except Exception as e:
                logger.warning(f"Ошибка удаления webhook: {e}")

            await self.bot.close()

        self.bot = None
        self.dp = None
        self._handlers_ready = False

        return {"status": "disconnected"}

    async def update_settings(self, **kwargs) -> IntegrationSuccessResponse:
        await self.disconnect()
        await self.connect()
        return IntegrationSuccessResponse(
            result={"status": "settings updated"}
        )

    # ==================== TELEGRAM WEBHOOK ====================

    async def handle_external(self, envelope: Dict) -> Dict:
        payload = envelope.get("body")

        if not isinstance(payload, dict):
            return IntegrationErrorResponse(
                result=IntegrationErrorModel(
                    error=400,
                    description="Invalid payload",
                )
            ).dict()

        try:
            await self._initialize_bot()
            update = types.Update.model_validate(payload)
            await self.dp.feed_update(self.bot, update)
        except Exception as e:
            logger.exception("Ошибка обработки Telegram update")
            return IntegrationErrorResponse(
                result=IntegrationErrorModel(
                    error=500,
                    description="Processing error",
                )
            ).dict()

        return {
            "status": "processed",
            "chat_id": extract_chat_id(payload) or "unknown",
        }