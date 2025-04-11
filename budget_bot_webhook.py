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
        [KeyboardButton(text="📈 Статистика"), KeyboardButton(text="💰 Остаток")],
        [KeyboardButton(text="➕ Доход"), KeyboardButton(text="💸 Расход")],
        [KeyboardButton(text="📊 По категориям"), KeyboardButton(text="📝 Категории")],
    ],
    resize_keyboard=True
)

default_categories = {
    "еда": ["еда", "продукты", "кафе", "ресторан"],
    "животные": ["корм", "кот", "собака", "ветеринар"],
    "транспорт": ["метро", "автобус", "такси", "машина", "транспорт", "бензин"],
    "развлечения": ["кино", "развлечения", "игры", "театр"],
    "техника": ["телефон", "ноутбук", "гаджет", "техника"],
    "прочее": []
}

class States(StatesGroup):
    expense = State()
    income = State()
    category = State()

@dp.message(CommandStart())
async def cmd_start(message: Message):
    user_id = message.from_user.id
    user_data[user_id]["categories"] = default_categories.copy()
    await message.answer("🎉 Добро пожаловать в бот учёта бюджета! Выберите действие:", reply_markup=main_kb)

@dp.message(F.text.lower().in_(["📈 статистика", "статистика"]))
async def full_stats(message: Message):
    user_id = message.from_user.id
    income = sum(i[0] for i in user_data[user_id]["income"])
    expenses = sum(e[0] for e in user_data[user_id]["expenses"])
    await message.answer(f"📊 Доходы: {income} ₽
📉 Расходы: {expenses} ₽")

@dp.message(F.text.lower().in_(["💰 остаток", "остаток", "баланс", "итого"]))
async def show_balance(message: Message):
    user_id = message.from_user.id
    income = sum(i[0] for i in user_data[user_id]["income"])
    expenses = sum(e[0] for e in user_data[user_id]["expenses"])
    await message.answer(f"💼 Баланс: {income - expenses} ₽")

@dp.message(F.text.lower().in_(["📊 по категориям", "по категориям"]))
async def choose_category_for_stats(message: Message):
    user_id = message.from_user.id
    categories = user_data[user_id]["categories"].keys()
    kb = ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=cat)] for cat in categories],
        resize_keyboard=True
    )
    await message.answer("📂 Выберите категорию для просмотра расходов:", reply_markup=kb)
    await dp.fsm.set_state(message.from_user.id, States.category)

@dp.message(States.category)
async def show_category_stats(message: Message, state: FSMContext):
    user_id = message.from_user.id
    selected = message.text.lower()
    stats = [e for e in user_data[user_id]["expenses"] if e[2] == selected]
    total = sum(e[0] for e in stats)
    if stats:
        lines = [f"• {amount} ₽ — {desc}" for amount, desc, _ in stats]
        await message.answer(f"📊 Расходы по категории '{selected}':
" + "
".join(lines) + f"

💸 Всего: {total} ₽")
    else:
        await message.answer(f"Нет расходов в категории '{selected}'")
    await state.clear()
    await message.answer("📋 Главное меню:", reply_markup=main_kb)

@dp.message(F.text.lower().in_(["📝 категории", "категории"]))
async def add_category(message: Message, state: FSMContext):
    await message.answer("✏️ Введите категорию и ключевые слова через запятую.
Пример: техника, ноутбук, телефон")
    await state.set_state(States.category)

@dp.message(States.category)
async def save_custom_category(message: Message, state: FSMContext):
    user_id = message.from_user.id
    parts = message.text.split(",")
    category = parts[0].strip().lower()
    keywords = [p.strip().lower() for p in parts[1:]]
    user_data[user_id]["categories"][category] = keywords
    await message.answer(f"✅ Категория '{category}' добавлена.")
    await state.clear()
    await message.answer("📋 Главное меню:", reply_markup=main_kb)

@dp.message(F.text.lower().in_(["➕ доход", "доход"]))
async def ask_income(message: Message, state: FSMContext):
    await message.answer("💰 Введите доход в формате: 50000 зарплата")
    await state.set_state(States.income)

@dp.message(States.income)
async def add_income(message: Message, state: FSMContext):
    user_id = message.from_user.id
    match = re.match(r"([+]?\d+)\s+(.+)", message.text)
    if match:
        amount = int(match.group(1))
        desc = match.group(2)
        user_data[user_id]["income"].append((amount, desc))
        await message.answer(f"✅ Доход {amount} ₽ добавлен: {desc}")
    else:
        await message.answer("❗ Неверный формат")
    await state.clear()

@dp.message(F.text.lower().in_(["💸 расход", "расход"]))
async def ask_expense(message: Message, state: FSMContext):
    await message.answer("✏️ Введите расход в формате: 1500 метро")
    await state.set_state(States.expense)

@dp.message(States.expense)
async def add_expense(message: Message, state: FSMContext):
    user_id = message.from_user.id
    match = re.match(r"(\d+)\s+(.+)", message.text)
    if match:
        amount = int(match.group(1))
        desc = match.group(2)
        category = "прочее"
        for cat, keys in user_data[user_id]["categories"].items():
            if any(k in desc.lower() for k in keys):
                category = cat
                break
        user_data[user_id]["expenses"].append((amount, desc, category))
        await message.answer(f"🔻 Расход {amount} ₽ добавлен: {desc} (категория: {category})")
    else:
        await message.answer("❗ Неверный формат.")
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