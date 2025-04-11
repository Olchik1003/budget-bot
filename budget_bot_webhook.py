import asyncio
import logging
import os
import re
from collections import defaultdict

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.client.default import DefaultBotProperties
from aiohttp import web
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application

API_TOKEN = os.getenv("API_TOKEN")
WEBHOOK_PATH = f"/webhook/{API_TOKEN}"
PORT = int(os.getenv("PORT", 10000))
BASE_WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL")

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

user_data = defaultdict(lambda: {"income": [], "expenses": [], "categories": {
    "еда": ["еда", "продукты"],
    "транспорт": ["метро", "такси", "автобус"],
    "развлечения": ["кино", "игры", "бар"],
    "прочее": []
}})

main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="💰 Остаток")],
        [KeyboardButton(text="📂 По категориям"), KeyboardButton(text="🗂 Категории")],
    ],
    resize_keyboard=True
)

class CategoryState(StatesGroup):
    editing = State()

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        '''👋 Привет! Я бот для учёта бюджета.
Просто отправь сообщение, например:

<code>+50000 зарплата</code>
<code>1200 метро</code>''',
        reply_markup=main_kb
    )

@dp.message(F.text.startswith("+"))
async def add_income(message: Message):
    try:
        amount, *desc = message.text[1:].split(" ", 1)
        amount = int(amount)
        description = desc[0] if desc else "Без описания"
        user_data[message.from_user.id]["income"].append((amount, description))
        await message.answer(f"💸 Доход <b>{amount} ₽</b> добавлен: {description}")
    except Exception:
        await message.answer(
            '''❗️ Неверный формат. Используйте:
<code>+50000 зарплата</code>'''
        )

@dp.message(lambda m: m.text and m.text[0].isdigit())
async def add_expense(message: Message):
    try:
        parts = message.text.split(" ", 1)
        amount = int(parts[0])
        description = parts[1] if len(parts) > 1 else "Без описания"
        uid = message.from_user.id
        categories = user_data[uid]["categories"]
        category = "прочее"
        for cat, keywords in categories.items():
            if any(word in description.lower() for word in keywords):
                category = cat
                break
        user_data[uid]["expenses"].append((amount, description, category))
        await message.answer(f"🧾 Расход <b>{amount} ₽</b> добавлен: {description} (категория: {category})")
    except Exception:
        await message.answer(
            '''❗️ Неверный формат. Используйте:
<code>1200 метро</code>'''
        )

async def on_startup(app):
    await bot.set_webhook(BASE_WEBHOOK_URL + WEBHOOK_PATH)

async def on_shutdown(app):
    await bot.delete_webhook()

app = web.Application()
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)
SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
setup_application(app, dp, bot=bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    web.run_app(app, host="0.0.0.0", port=PORT)