import pandas as pd
from io import BytesIO
import asyncio
import logging

from aiogram import Router, F
from aiogram.types import (
    Message, CallbackQuery, BufferedInputFile,
)
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

logger = logging.getLogger(__name__)

router = Router()


# -----------------------------
# /start
# -----------------------------
@router.message(Command("start"))
async def start_cmd(message: Message):
    await message.answer(
        "Я бот для контроля остатков товаров на складах.\n\n"
        "Напишите название товара или используйте команды из меню."
    )


# -----------------------------
# /stock
# -----------------------------
@router.message(Command("stock"))
async def search_cmd(message: Message):
    await message.answer("Введите название товара для поиска:")


# -----------------------------
# /minimum → выбор склада
# -----------------------------
@router.message(Command("minimum"))
async def low_stock_cmd(message: Message):
    stocks = await message.bot.client.get_stocks()
    if not stocks:
        await message.answer("Склады не найдены")
        return

    kb = InlineKeyboardBuilder()
    for s in stocks:
        kb.button(text=s["name"], callback_data=f"min_{s['id']}")
    kb.adjust(1)

    await message.answer("Выберите склад:", reply_markup=kb.as_markup())


# -----------------------------
# Обработчик нажатия "min_ID"
# -----------------------------
@router.callback_query(F.data.startswith("min_"))
async def show_minimum(callback: CallbackQuery):
    stock_id = int(callback.data.split("_")[1])
    client = callback.bot.client

    try:
        # Получаем имя склада
        stocks = await client.get_stocks()
        stock_name = next((s["name"] for s in stocks if s["id"] == stock_id), "Склад")

        # Получаем товары
        items = await client.get_items()
        if not items:
            await callback.message.edit_text("Нет товаров в системе.")
            return

        quantities = await client.get_current_quantity(
            [i["id"] for i in items], [stock_id]
        )

        # Формируем список товаров с низким остатком
        low = []
        for item in items:
            qty = quantities.get(item["id"], {}).get(stock_id, 0)
            if qty <= item.get("min_quantity", 0):
                low.append({
                    "Товар": item["name"],
                    "Остаток": qty,
                    "Мин.": item.get("min_quantity", 0)
                })

        if not low:
            await callback.message.edit_text(
                f"На складе «{stock_name}» всё в норме! ✅"
            )
            return

        # Создаём Excel-файл в памяти
        df = pd.DataFrame(low)
        bio = BytesIO()
        df.to_excel(bio, index=False, engine="openpyxl")
        bio.seek(0)

        file_size = len(bio.getvalue())
        logger.info(f"Формируем файл {file_size} bytes для склада {stock_name}")

        await callback.message.edit_text(
            f"Файл с низким остатком для склада «{stock_name}» готов, отправляем..."
        )

        # -------------------------
        # Функция отправки файла с retry
        # -------------------------
        async def send_file_with_retry(chat_id, bio, caption, retries=3):
            file = BufferedInputFile(
                file=bio.getvalue(),
                filename=f"Минимальные_остатки_{stock_name}.xlsx"
            )

            for attempt in range(1, retries + 1):
                try:
                    await callback.bot.send_document(
                        chat_id=chat_id,
                        document=file,
                        caption=caption
                    )
                    logger.info(f"Файл отправлен в чат {chat_id}")
                    return True

                except Exception as e:
                    logger.warning(f"Попытка {attempt} не удалась: {e}")

                    if attempt == retries:
                        raise

                    await asyncio.sleep(2)

        # Отправка файла
        await send_file_with_retry(
            chat_id=callback.from_user.id,
            bio=bio,
            caption=f"Склад: {stock_name}\nТоваров с низким остатком: {len(low)}"
        )

    except Exception as e:
        logger.error(f"Ошибка в show_minimum: {e}")
        try:
            await callback.message.edit_text(
                "Произошла ошибка при загрузке данных или отправке файла."
            )
        except:
            pass


# -----------------------------
# Поиск товаров (обычный текст)
# -----------------------------
@router.message(F.text)
async def search_item(message: Message):
    query = message.text.strip().lower()
    if len(query) < 2:
        return await message.reply("Слишком короткий запрос")

    items = await message.bot.client.get_items()
    items = [i for i in items if query in i["name"].lower()]

    if not items:
        return await message.reply("Ничего не найдено")

    stocks = await message.bot.client.get_stocks()
    stock_ids = [s["id"] for s in stocks]
    quantities = await message.bot.client.get_current_quantity(
        [i["id"] for i in items],
        stock_ids
    )

    lines = []
    for item in items[:10]:
        q = quantities.get(item["id"], {})
        total = sum(q.values())
        status = "Мало" if total <= item.get("min_quantity", 0) else "OK"

        lines.append(
            f"*{item['name']}*\n"
            f"Всего: {total} | Статус: {status}\n" +
            "\n".join(f"{s['name']}: {q.get(s['id'], 0)}" for s in stocks)
        )

    await message.reply("\n\n".join(lines), parse_mode="Markdown")
