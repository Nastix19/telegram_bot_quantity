import logging
from sqlalchemy import select
from app.core.db import get_session
from app.models.integration_account import IntegrationAccount
from app.bot.manager import bot_manager

logger = logging.getLogger(__name__)

async def get_account_by_id(account_id: str) -> IntegrationAccount | None:
    async for session in get_session():
        result = await session.execute(
            select(IntegrationAccount).where(IntegrationAccount.regos_account_id == account_id)
        )
        return result.scalar_one_or_none()

async def warmup_bots():
    async for session in get_session():
        result = await session.execute(select(IntegrationAccount))
        accounts = result.scalars().all()
        logger.info(f"Найдено {len(accounts)} аккаунтов")
        for acc in accounts:
            if acc.bot_token:
                try:
                    await bot_manager.ensure(acc)
                    logger.info(f"Бот запущен: {acc.regos_account_id}")
                except Exception as e:
                    logger.error(f"Ошибка запуска бота {acc.regos_account_id}: {e}")
        break