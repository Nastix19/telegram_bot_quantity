import asyncio
from aiogram import Bot, Dispatcher
from handlers import start, stock

TELEGRAM_TOKEN = "8340376388:AAFIxZiyawsbJ2W9q1dpqD9gB2GugLSeC0Q"

bot = Bot(token=TELEGRAM_TOKEN)
dp = Dispatcher()

async def main():
    dp.include_router(start.router)
    dp.include_router(stock.router)

    await start.set_bot_commands(bot)
    await dp.start_polling(bot, skip_updates=True)

if __name__ == "__main__":
    asyncio.run(main())
