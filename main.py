from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.core.db import init_db
from app.bot.manager import bot_manager
from app.api import integration_router, bot_router

@asynccontextmanager
async def lifespan(app: FastAPI):
    await init_db()
    yield
    await bot_manager.shutdown()

app = FastAPI(lifespan=lifespan)

app.include_router(integration_router.router)
app.include_router(bot_router.router, prefix="/webhook")

@app.get("/")
async def root():
    return {"status": "REGOS Quantity Bot — работает!"}
