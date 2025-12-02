import pandas as pd
from io import BytesIO
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery, BufferedInputFile
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder

router = Router()

@router.message(Command("start"))
async def start(message: Message):
    await message.answer(
        "Я бот для контроля остатков товаров на складах.\n\n"
        "Напишите название товара или используйте команды из меню."
    )

@router.message(Command("stock"))
async def search_cmd(message: Message):
    await message.answer("Введите название товара для поиска:")

@router.message(Command("minimum"))
async def minimum(message: Message):
    stocks = await message.bot.client.get_stocks()
    if not stocks:
        return await message.answer("Склады не найдены")

    kb = InlineKeyboardBuilder()
    for s in stocks:
        kb.button(text=s["name"], callback_data=f"min_{s['id']}")
    kb.adjust(1)
    await message.answer("Выберите склад:", reply_markup=kb.as_markup())

@router.callback_query(F.data.startswith("min_"))
async def show_minimum(callback: CallbackQuery):
    stock_id = int(callback.data.split("_")[1])
    client = callback.bot.client

    try:
        await callback.answer()

        stocks = await client.get_stocks()
        stock_name = next((s["name"] for s in stocks if s["id"] == stock_id), "Склад")

        items = await client.get_items()
        if not items:
            return await callback.message.edit_text("Нет товаров на складе")

        loading_msg = await callback.message.edit_text("Загружаю данные...")

        quantities = await client.get_current_quantity([i["id"] for i in items], [stock_id])

        low = [
            {"Товар": i["name"], "Остаток": quantities.get(i["id"], {}).get(stock_id, 0), "Мин.": i.get("min_quantity", 0)}
            for i in items
            if quantities.get(i["id"], {}).get(stock_id, 0) <= i.get("min_quantity", 0)
        ]

        if not low:
            return await callback.message.edit_text(f"На складе «{stock_name}» товары в норме!")

        df = pd.DataFrame(low)
        bio = BytesIO()
        df.to_excel(bio, index=False, engine="openpyxl")
        bio.seek(0)

        file = BufferedInputFile(bio.getvalue(), filename=f"Минимальные_остатки_{stock_name}.xlsx")

        await callback.bot.send_document(
            chat_id=callback.from_user.id,
            document=file,
            caption=f"Минимальные остатки\nСклад: {stock_name}\nТоваров ниже минимума:: {len(low)}",
            parse_mode = "Markdown"
        )

        await loading_msg.delete()

    except Exception as e:
        await callback.message.edit_text("Ошибка при загрузке данных")

@router.message(F.text)
async def search(message: Message):
    query = message.text.strip().lower()
    if len(query) < 2:
        return

    items = await message.bot.client.get_items()
    found = [i for i in items if query in i["name"].lower()][:10]

    if not found:
        return await message.answer("Ничего не найдено")

    stocks = await message.bot.client.get_stocks()
    quantities = await message.bot.client.get_current_quantity([i["id"] for i in found], [s["id"] for s in stocks])

    lines = []
    for item in found:
        q = quantities.get(item["id"], {})
        total = sum(q.values())
        status = "Мало" if total <= item.get("min_quantity", 0) else "OK"
        lines.append(
            f"*{item['name']}*\n"
            f"Всего: {total} | {status}\n" +
            "\n".join(f"{s['name']}: {q.get(s['id'], 0)}" for s in stocks)
        )

    await message.answer("\n\n".join(lines), parse_mode="Markdown")