# utils.py

from aiogram import Bot
from config import PUBLIC_URL
import aiohttp

async def set_telegram_webhook(bot_token: str, connected_integration_id: str):
    bot = Bot(token=bot_token)

    webhook_url = f"{PUBLIC_URL}/telegram/webhook/{connected_integration_id}"
    secret_token = connected_integration_id  # используется для проверки подлинности

    async with aiohttp.ClientSession() as session:
        async with session.post(
            f"https://api.telegram.org/bot{bot_token}/setWebhook",
            json={
                "url": webhook_url,
                "secret_token": secret_token
            }
        ) as resp:
            if resp.status != 200:
                raise Exception(f"Failed to set webhook: {resp.status}")
