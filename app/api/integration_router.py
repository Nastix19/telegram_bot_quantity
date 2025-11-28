# app/api/integration_router.py — РАБОТАЕТ НА SQLALCHEMY 2.0+
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy import select
from app.models.integration_account import IntegrationAccount
from app.core.db import AsyncSessionLocal
from app.bot.manager import bot_manager
import logging

logger = logging.getLogger(__name__)
router = APIRouter()

@router.post("/")
async def regos_webhook(request: Request):
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(400, "Invalid JSON")

    action = payload.get("action")
    conn_id = payload.get("connected_integration_id")
    data = payload.get("data", {})

    if not action or not conn_id:
        raise HTTPException(400, "Missing action or connected_integration_id")

    async with AsyncSessionLocal() as db:
        # ПРАВИЛЬНЫЙ СИНТАКСИС ДЛЯ SQLALCHEMY 2.filter_by() или .where()
        result = await db.execute(
            select(IntegrationAccount).where(
                IntegrationAccount.connected_integration_id == conn_id
            )
        )
        account = result.scalar_one_or_none()

        # === Connect ===
        if action == "Connect":
            if not account:
                account = IntegrationAccount(
                    connected_integration_id=conn_id,
                    integration_url="",
                    bot_token=None,
                    title="REGOS Client"
                )
                db.add(account)
                await db.commit()
                logger.info(f"Connect: создан аккаунт {conn_id}")
            return {"status": "ok"}

        # === UpdateSettings ===
        if action == "UpdateSettings":
            settings = data.get("settings", [])
            bot_token = None
            integration_url = None

            for s in settings:
                if s.get("name_var") == "BOT_TOKEN":
                    bot_token = s.get("value")
                if s.get("name_var") == "INTEGRATION_URL":
                    integration_url = s.get("value")

            if not account:
                account = IntegrationAccount(
                    connected_integration_id=conn_id,
                    integration_url=integration_url or "",
                    bot_token=bot_token,
                    title="REGOS Client"
                )
                db.add(account)
            else:
                if bot_token is not None:
                    account.bot_token = bot_token
                if integration_url is not None:
                    account.integration_url = integration_url

            await db.commit()

            # Запускаем бота, если есть всё нужное
            if account.bot_token and account.integration_url:
                await bot_manager.ensure(account)
                logger.info(f"Бот успешно запущен: {conn_id}")

            return {"status": "ok"}