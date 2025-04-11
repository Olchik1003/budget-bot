import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, F
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from collections import defaultdict

API_TOKEN = os.getenv("API_TOKEN")
BASE_WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL")
WEBHOOK_PATH = f"/webhook/{API_TOKEN}"
PORT = int(os.getenv("PORT", 10000))

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

user_data = defaultdict(lambda: {"income": [], "expenses": []})

main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="💰 Остаток")],
        [KeyboardButton(text="📈 Категории")]
    ],
    resize_keyboard=True
)

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        """👋 Привет! Я бот для учёта бюджета.
Просто отправь сообщение, например:

+50000 зарплата
1200 метро""",
        reply_markup=main_kb
    )

@dp.message(F.text == "📊 Статистика")
async def stats(message: Message):
    uid = message.from_user.id
    income = sum(i[0] for i in user_data[uid]["income"])
    expenses = sum(i[0] for i in user_data[uid]["expenses"])
    await message.answer(f"📈 Доходы: {income} ₽
📉 Расходы: {expenses} ₽")

@dp.message(F.text == "💰 Остаток")
async def balance(message: Message):
    uid = message.from_user.id
    income = sum(i[0] for i in user_data[uid]["income"])
    expenses = sum(i[0] for i in user_data[uid]["expenses"])
    await message.answer(f"💼 Баланс: {income - expenses} ₽")

@dp.message(F.text == "📈 Категории")
async def categories(message: Message):
    await message.answer(
        """✏️ Введите новую категорию и ключевые слова через запятую.
Пример: техника, ноутбук, телефон"""
    )

async def on_startup(bot: Bot):
    webhook_url = f"{BASE_WEBHOOK_URL}{WEBHOOK_PATH}"
    await bot.set_webhook(webhook_url)

async def main():
    logging.basicConfig(level=logging.INFO)
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    await on_startup(bot)
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == "__main__":
    asyncio.run(main())