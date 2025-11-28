from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPBasic, HTTPBasicCredentials
from app.core.config import settings
from app.services.integration_service import get_account_by_id
from sqlalchemy.ext.asyncio import AsyncSession
from app.core.db import get_session
from app.models.integration_account import IntegrationAccount
import secrets

router = APIRouter(prefix="/admin", tags=["admin"])
security = HTTPBasic()

def verify_admin(credentials: HTTPBasicCredentials = Depends(security)):
    correct_username = secrets.compare_digest(credentials.username, settings.admin_username or "")
    correct_password = secrets.compare_digest(credentials.password, settings.admin_password or "")
    if not (correct_username and correct_password):
        raise HTTPException(status_code=401, detail="Неверный логин или пароль", headers={"WWW-Authenticate": "Basic"})
    return True

@router.get("/", response_class=HTMLResponse)
async def admin_panel(_: bool = Depends(verify_admin), session: AsyncSession = Depends(get_session)):
    result = await session.execute(IntegrationAccount.__table__.select().order_by(IntegrationAccount.id))
    accounts = result.fetchall()
    rows = "".join(
        f"<tr><td>{a.regos_account_id}</td><td>{a.title or '-'}</td><td>{'Работает' if a.bot_token else 'Нет токена'}</td></tr>"
        for a in accounts
    )
    return f"""
    <html><head><title>Админка</title><style>table{{border-collapse:collapse;width:100%}}td,th{{border:1px solid #ccc;padding:8px}}</style></head>
    <body><h1>Подключённые аккаунты REGOS</h1>
    <table><tr><th>ID</th><th>Название</th><th>Статус бота</th></tr>{rows}</table>
    <p>Всего: {len(accounts)}</p>
    </body></html>
    """