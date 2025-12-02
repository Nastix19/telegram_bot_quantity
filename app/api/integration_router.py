# integration_router.py
from fastapi import APIRouter, Request, HTTPException
from sqlalchemy import select
from app.models.integration_account import IntegrationAccount
from app.core.db import AsyncSessionLocal
from app.bot.manager import bot_manager

router = APIRouter()

@router.post("/")
async def regos_webhook(request: Request):
    payload = await request.json()
    action = payload.get("action")
    conn_id = payload.get("connected_integration_id")

    async with AsyncSessionLocal() as db:
        account = (await db.execute(
            select(IntegrationAccount).where(IntegrationAccount.connected_integration_id == conn_id)
        )).scalar_one_or_none()

        if action == "Connect":
            if not account:
                account = IntegrationAccount(connected_integration_id=conn_id, integration_url="", bot_token=None)
                db.add(account)
                await db.commit()

        elif action == "UpdateSettings":
            settings = payload.get("data", {}).get("settings", [])
            bot_token = next((s["value"] for s in settings if s.get("name_var") == "BOT_TOKEN"), None)
            url = next((s["value"] for s in settings if s.get("name_var") == "INTEGRATION_URL"), None)

            if not account:
                account = IntegrationAccount(connected_integration_id=conn_id, integration_url=url or "", bot_token=bot_token)
                db.add(account)
            else:
                if bot_token: account.bot_token = bot_token
                if url: account.integration_url = url
            await db.commit()

            if account.bot_token and account.integration_url:
                await bot_manager.ensure(account)

        return {"status": "ok"}