# main.py
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.bot.manager import bot_manager
from app.api import integration_router, bot_router
from app.core.db import create_db_and_tables as create_tables

@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    print("Сервис запущен")
    yield
    print("Останавливаем боты...")
    await bot_manager.shutdown()

app = FastAPI(lifespan=lifespan)


app.include_router(integration_router.router)
app.include_router(bot_router.router, prefix="/webhook")

@app.get("/")
async def root():
    return {"status": "ok", "message": "REGOS Quantity Bot работает!"}