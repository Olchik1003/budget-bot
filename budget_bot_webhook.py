import os
import re
import logging
from collections import defaultdict

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.types import Message, KeyboardButton, ReplyKeyboardMarkup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiohttp import web

API_TOKEN = os.getenv("API_TOKEN")
WEBHOOK_PATH = f"/webhook/{API_TOKEN}"
WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL", "") + WEBHOOK_PATH

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
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
        [KeyboardButton(text="📈 По категориям"), KeyboardButton(text="🗂 Категории")],
    ],
    resize_keyboard=True
)

@dp.message(F.text == "/start")
async def start(message: Message):
    await message.answer(
        '''👋 Привет! Я бот для учёта бюджета.
Просто отправь сообщение, например:

<code>+50000 зарплата</code>
<code>1200 метро</code>''',
        reply_markup=main_kb
    )

@dp.message(F.text == "📊 Статистика")
async def stats(message: Message):
    user_id = message.from_user.id
    income = sum(i[0] for i in user_data[user_id]["income"])
    expenses = sum(e[0] for e in user_data[user_id]["expenses"])
    await message.answer(f"📊 Доходы: {income} ₽\n💸 Расходы: {expenses} ₽")

@dp.message(F.text == "💰 Остаток")
async def balance(message: Message):
    user_id = message.from_user.id
    income = sum(i[0] for i in user_data[user_id]["income"])
    expenses = sum(e[0] for e in user_data[user_id]["expenses"])
    await message.answer(f"💼 Остаток: {income - expenses} ₽")

@dp.message(F.text == "📈 По категориям")
async def stats_by_category(message: Message):
    user_id = message.from_user.id
    category_totals = defaultdict(int)
    for amount, _, category in user_data[user_id]["expenses"]:
        category_totals[category] += amount
    if not category_totals:
        await message.answer("❗ Пока нет расходов по категориям.")
        return
    text = "📊 Расходы по категориям:\n"
    for cat, total in category_totals.items():
        text += f"• {cat.capitalize()}: {total} ₽\n"
    await message.answer(text)

@dp.message(F.text == "🗂 Категории")
async def categories(message: Message):
    user_id = message.from_user.id
    cats = user_data[user_id]["categories"]
    text = "📂 Текущие категории:\n"
    for cat, keys in cats.items():
        text += f"• {cat}: {', '.join(keys)}\n"
    await message.answer(text)

@dp.message()
async def handle_entry(message: Message):
    user_id = message.from_user.id
    text = message.text.strip()
    if match := re.match(r"^\+?(\d+)\s*(.*)", text):
        amount = int(match[1])
        description = match[2] or "Без описания"
        if text.startswith("+"):
            user_data[user_id]["income"].append((amount, description))
            await message.answer(f"✅ Доход {amount} ₽ добавлен: {description}")
        else:
            category = "прочее"
            for cat, keys in user_data[user_id]["categories"].items():
                if any(k in description.lower() for k in keys):
                    category = cat
                    break
            user_data[user_id]["expenses"].append((amount, description, category))
            await message.answer(f"🔻 Расход {amount} ₽ добавлен: {description} (категория: {category})")
    else:
        await message.answer("❗ Неверный формат. Используйте:\n<code>+50000 зарплата</code>\n<code>1200 метро</code>")

async def on_startup(app: web.Application):
    await bot.set_webhook(WEBHOOK_URL)

app = web.Application()
dp.startup.register(on_startup)
SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
setup_application(app, dp, bot=bot)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    web.run_app(app, host="0.0.0.0", port=int(os.getenv("PORT", 10000)))