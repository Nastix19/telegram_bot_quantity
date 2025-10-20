import os
import pandas as pd
from aiogram import types, F, Router
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from services.regos_client import RegosClient

router = Router()

# Работа с API
client = RegosClient(
    base_url="https://integration.regos.uz/gateway/out/25441b5b52594dbf8cc9717a8fe0b22c/v1"
)

@router.message(Command("stock"))
async def search_cmd(message: types.Message):
    await message.answer("Введите название товара для поиска:")

@router.message(Command("minimum"))
async def low_stock_cmd(message: types.Message):
    stocks = client.get_stocks()
    if not stocks:
        await message.answer("Склады не найдены")
        return

    kb = InlineKeyboardBuilder()
    for stock in stocks:
        kb.button(text=stock["name"], callback_data=f"stock_{stock['id']}")
    kb.adjust(1)
    await message.answer("Выберите склад:", reply_markup=kb.as_markup())

@router.callback_query(lambda c: c.data and c.data.startswith("stock_"))
async def show_minimum_for_stock(callback: types.CallbackQuery):
    stock_id = int(callback.data.split("_")[1])
    await callback.message.edit_text("Загружаю данные...")

    stocks = client.get_stocks()
    stock_name = next((s["name"] for s in stocks if s["id"] == stock_id), f"ID {stock_id}")

    items = client.get_items(limit=1000)
    item_ids = [i["id"] for i in items]
    min_by_id = {i["id"]: i.get("min_quantity", 0) for i in items}

    quantities = client.get_current_quantity(item_ids=item_ids, stock_ids=[stock_id])

    low_stock_data = []
    for item in items:
        current_qty = quantities.get(item["id"], {}).get(stock_id)
        if current_qty is None:
            continue
        min_qty = min_by_id.get(item["id"], 0)
        if current_qty <= min_qty:
            low_stock_data.append({
                "Товар": item["name"],
                "Остаток": current_qty,
                "Мин. остаток": min_qty
            })

    if not low_stock_data:
        await callback.message.edit_text(f"На складе '{stock_name}' все товары в норме.")
        return

    df = pd.DataFrame(low_stock_data)
    safe_stock_name = "".join(c if c.isalnum() or c in ("_", "-") else "_" for c in stock_name)
    file_name = f"Минимальные_остатки_{safe_stock_name}.xlsx"
    file_path = os.path.join(os.getcwd(), file_name)
    df.to_excel(file_path, index=False)

    await callback.message.answer_document(
        document=types.FSInputFile(file_path),
        caption=f"Минимальные остатки по складу '{stock_name}'"
    )

    os.remove(file_path)

@router.message(F.text)
async def handle_text(message: types.Message):
    query = message.text.strip().lower()
    if not query:
        await message.reply("Введите название товара для поиска.")
        return

    items = client.get_items(limit=1000)
    found = [i for i in items if query in i["name"].lower()]

    if not found:
        await message.reply("Товар не найден")
        return

    stocks = client.get_stocks()
    stock_ids = [s["id"] for s in stocks]
    item_ids = [i["id"] for i in found]
    quantities = client.get_current_quantity(item_ids=item_ids, stock_ids=stock_ids)

    reply = []
    for item in found:
        stock_qtys = quantities.get(item["id"], {})
        total_qty = sum(stock_qtys.values())
        min_qty = item.get("min_quantity", 0)
        status = "Мало" if total_qty <= min_qty else "Достаточно"

        stock_lines = [f"{s['name']}: {stock_qtys.get(s['id'], 0)}" for s in stocks]
        reply.append(
            f"*{item['name']}*\n"
            f"Мин. остаток: {min_qty}\n"
            f"Всего: {total_qty}\n"
            f"Статус: {status}\n\n" +
            "\n".join(stock_lines)
        )

    await message.reply("\n\n".join(reply), parse_mode="Markdown")
