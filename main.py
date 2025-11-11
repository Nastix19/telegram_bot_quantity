# main.py

from fastapi import FastAPI
from database import init_db
from regos_router import router as regos_router
from telegram_router import router as telegram_router

app = FastAPI(title="Telegram Bot Quantity Backend")

# Инициализация базы данных
init_db()

# Подключение маршрутов
app.include_router(regos_router)
app.include_router(telegram_router)

@app.on_event("startup")
async def on_startup():
    print("Backend запущен и готов принимать вебхуки от Telegram")

