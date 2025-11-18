import os
import pandas as pd
from aiogram import types, F, Router
from aiogram.filters import Command
from aiogram.utils.keyboard import InlineKeyboardBuilder
from services.regos_client import RegosClient
from typing import Optional

router = Router()

_client: Optional[RegosClient] = None

def set_client(base_url: str):
    global _client
    _client = RegosClient(base_url=base_url)

def _get_client() -> RegosClient:
    if _client is None:
        raise RuntimeError("RegosClient не инициализирован. Вызывайте set_client(base_url).")
    return _client

#  КОМАНДА /stock
@router.message(Command("stock"))
async def search_cmd(message: types.Message):
    await message.answer("Введите название товара для поиска:")

#  КОМАНДА /minimum
@router.message(Command("minimum"))
async def low_stock_cmd(message: types.Message):
    client = _get_client()  # Получаем текущий клиент
    stocks = client.get_stocks()
    if not stocks:
        await message.answer("Склады не найдены")
        return

    kb = InlineKeyboardBuilder()
    for stock in stocks:
        kb.button(
            text=stock.get("name", f"ID {stock.get('id')}"),
            callback_data=f"stock_{stock.get('id')}"
        )
    kb.adjust(1)
    await message.answer("Выберите склад:", reply_markup=kb.as_markup())

#  ВЫБОР СКЛАДА
@router.callback_query(lambda c: c.data and c.data.startswith("stock_"))
async def show_minimum_for_stock(callback: types.CallbackQuery):
    client = _get_client()  # Получаем текущий клиент

    try:
        stock_id = int(callback.data.split("_", 1)[1])
    except Exception:
        await callback.answer("Некорректные данные", show_alert=True)
        return

    await callback.message.edit_text("Загружаю данные...")

    stocks = client.get_stocks()
    stock_name = next(
        (s.get("name") for s in stocks if s.get("id") == stock_id),
        f"ID {stock_id}"
    )

    items = client.get_items(limit=1000)
    item_ids = [i.get("id") for i in items if "id" in i]
    min_by_id = {i.get("id"): i.get("min_quantity", 0) for i in items if "id" in i}

    quantities = client.get_current_quantity(
        item_ids=item_ids,
        stock_ids=[stock_id]
    )

    low_stock_data = []
    for item in items:
        item_id = item.get("id")
        if item_id is None:
            continue
        current_qty = quantities.get(item_id, {}).get(stock_id)
        if current_qty is None:
            continue
        min_qty = min_by_id.get(item_id, 0)
        if current_qty <= min_qty:
            low_stock_data.append({
                "Товар": item.get("name", ""),
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

    try:
        await callback.message.answer_document(
            document=types.FSInputFile(file_path),
            caption=f"Минимальные остатки по складу '{stock_name}'"
        )
    finally:
        try:
            os.remove(file_path)
        except Exception:
            pass

#  ПОИСК ПО НАЗВАНИЮ
@router.message(F.text & ~F.text.startswith("/"))
async def handle_text(message: types.Message):
    client = _get_client()  # Получаем текущий клиент

    query = message.text.strip().lower()
    if not query:
        await message.reply("Введите название товара для поиска.")
        return

    items = client.get_items(limit=1000)
    found = [i for i in items if query in (i.get("name") or "").lower()]

    if not found:
        await message.reply("Товар не найден")
        return

    stocks = client.get_stocks()
    stock_ids = [s.get("id") for s in stocks if "id" in s]
    item_ids = [i.get("id") for i in found if "id" in i]
    quantities = client.get_current_quantity(item_ids=item_ids, stock_ids=stock_ids)

    reply_lines = []
    for item in found:
        iid = item.get("id")
        stock_qtys = quantities.get(iid, {}) if iid is not None else {}
        total_qty = sum(stock_qtys.values()) if stock_qtys else 0
        min_qty = item.get("min_quantity", 0)
        status = "Мало" if total_qty <= min_qty else "Достаточно"

        stock_lines = [f"{s.get('name')}: {stock_qtys.get(s.get('id'), 0)}" for s in stocks]
        reply_lines.append(
            f"*{item.get('name', '')}*\n"
            f"Мин. остаток: {min_qty}\n"
            f"Всего: {total_qty}\n"
            f"Статус: {status}\n\n" +
            "\n".join(stock_lines)
        )

    await message.reply("\n\n".join(reply_lines), parse_mode="Markdown")
