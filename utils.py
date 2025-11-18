from aiogram import Bot
from config import PUBLIC_URL
import aiohttp
import logging

logger = logging.getLogger("utils")

async def set_telegram_webhook(bot_token: str, connected_integration_id: str):
    """


    """
    webhook_url = f"{PUBLIC_URL}/telegram/webhook/{connected_integration_id}"
    secret_token = connected_integration_id

    logger.info(f"Setting webhook for {connected_integration_id}: {webhook_url}")

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"https://api.telegram.org/bot{bot_token}/setWebhook",
            json={
                "url": webhook_url,
                "secret_token": secret_token
            }
        ) as resp:
            text = await resp.text()
            if resp.status != 200:
                logger.error(f"Failed to set webhook: {resp.status} {text}")
                raise Exception(f"Failed to set webhook: {resp.status} {text}")
            logger.info(f"Webhook set successfully for {connected_integration_id}: {text}")
