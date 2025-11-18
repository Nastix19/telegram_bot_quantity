# handlers/start.py
from aiogram import types
from aiogram.filters import Command
from aiogram.types import BotCommand
from aiogram import Router

router = Router()

@router.message(Command("start"))
async def start_cmd(message: types.Message):
    await message.answer(
        "\nЯ бот для контроля остатков товаров на складах.\n\n"
        "Выберите действие из меню или напишите название товара для поиска",
    )

async def set_bot_commands(bot):
    commands = [
        BotCommand(command="start", description="Старт бота"),
        BotCommand(command="stock", description="Поиск товара"),
        BotCommand(command="minimum", description="Минимальные остатки"),
    ]
    try:
        await bot.set_my_commands(commands)
    except Exception:
        pass

