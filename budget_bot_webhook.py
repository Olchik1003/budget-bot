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
    await message.answer(f"📊 Доходы: {income} ₽\n📉 Расходы: {expenses} ₽")

@dp.message(F.text.lower().in_(["💰 остаток", "остаток", "баланс", "итого"]))
async def show_balance(message: Message):
    user_id = message.from_user.id
    income = sum(i[0] for i in user_data[user_id]["income"])
    expenses = sum(e[0] for e in user_data[user_id]["expenses"])
    await message.answer(f"💼 Баланс: {income - expenses} ₽")

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