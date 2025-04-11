import asyncio
import logging
import os
import re
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from collections import defaultdict

API_TOKEN = os.getenv("API_TOKEN")
WEBHOOK_PATH = f"/webhook/{API_TOKEN}"
WEBHOOK_URL = "https://budget-bot-8lfi.onrender.com" + WEBHOOK_PATH

bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

user_data = defaultdict(lambda: {"income": [], "expenses": [], "categories": {}})

main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📈 Статистика")],
        [KeyboardButton(text="➕ Доход"), KeyboardButton(text="💸 Расход")],
        [KeyboardButton(text="📊 По категориям"), KeyboardButton(text="💰 Остаток")],
        [KeyboardButton(text="📝 Категории"), KeyboardButton(text="❌ Удалить запись")],
    ],
    resize_keyboard=True
)

default_categories = {
    "еда": ["еда", "продукты"],
    "животные": ["корм", "кот", "собака", "животные"],
    "транспорт": ["метро", "автобус", "транспорт"],
    "развлечения": ["кино", "развлечения", "игры"],
    "прочее": []
}

class ExpenseState(StatesGroup):
    waiting_for_expense = State()

class IncomeState(StatesGroup):
    waiting_for_income = State()

class CategoryState(StatesGroup):
    editing_category = State()

class DeleteState(StatesGroup):
    choosing_delete = State()

@dp.message(CommandStart())
async def start(message: Message):
    user_id = message.from_user.id
    user_data[user_id]["categories"] = default_categories.copy()
    await message.answer("🎉 Добро пожаловать в бот учёта бюджета! 📊", reply_markup=main_kb)

@dp.message(F.text == "➕ Доход")
async def income_start(message: Message, state: FSMContext):
    await message.answer("💰 Введите сумму дохода, например: +50000 зарплата")
    await state.set_state(IncomeState.waiting_for_income)

@dp.message(IncomeState.waiting_for_income)
async def add_income(message: Message, state: FSMContext):
    user_id = message.from_user.id
    match = re.match(r"[+]?([\d]+)(?:\s+(.+))?", message.text)
    if match:
        amount = int(match.group(1))
        description = match.group(2) or "Без описания"
        user_data[user_id]["income"].append((amount, description))
        await message.answer(f"✅ Доход {amount} ₽ добавлен: {description}")
    else:
        await message.answer("❗ Неверный формат. Попробуйте снова.")
    await state.clear()

@dp.message(F.text == "💸 Расход")
async def expense_start(message: Message, state: FSMContext):
    await message.answer("🧾 Введите расход, например: 1000 корм для кошки")
    await state.set_state(ExpenseState.waiting_for_expense)

@dp.message(ExpenseState.waiting_for_expense)
async def add_expense(message: Message, state: FSMContext):
    user_id = message.from_user.id
    match = re.match(r"(\d+)\s+(.+)", message.text)
    if match:
        amount = int(match.group(1))
        description = match.group(2)
        category = "прочее"
        for cat, keywords in user_data[user_id]["categories"].items():
            if any(k in description.lower() for k in keywords):
                category = cat
                break
        user_data[user_id]["expenses"].append((amount, description, category))
        await message.answer(f"🔻 Расход {amount} ₽ добавлен: {description} (категория: {category})")
    else:
        await message.answer("❗ Неверный формат. Попробуйте снова.")
    await state.clear()

async def on_startup(bot: Bot):
    await bot.set_webhook(WEBHOOK_URL)

async def on_shutdown(bot: Bot):
    await bot.delete_webhook()
    await bot.session.close()

async def main():
    logging.basicConfig(level=logging.INFO)
    app = web.Application()
    setup_application(app, dp, bot=bot)

    webhook_handler = SimpleRequestHandler(dispatcher=dp, bot=bot)
    webhook_handler.register(app, path=WEBHOOK_PATH)

    dp.startup.register(on_startup)
    dp.shutdown.register(on_shutdown)

    return app

if __name__ == "__main__":
    web.run_app(main(), host="0.0.0.0", port=int(os.getenv("PORT", 8000)))