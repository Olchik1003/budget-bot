import asyncio
import logging
import os
from collections import defaultdict

from aiogram import Bot, Dispatcher, F
from aiogram.enums import ParseMode
from aiogram.filters import CommandStart
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ContentType
from aiogram.client.default import DefaultBotProperties
from aiohttp import web

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
        """👋 Привет! Я бот для учёта бюджета.
Просто отправь сообщение, например:

<code>+50000 зарплата</code>
<code>1200 метро</code>""",
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
        await message.answer("❗️ Неверный формат. Используйте:
<code>+50000 зарплата</code>")

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
        await message.answer("❗️ Неверный формат. Используйте:
<code>1200 метро</code>")

@dp.message(F.text == "📊 Статистика")
async def show_stats(message: Message):
    uid = message.from_user.id
    income = sum(i[0] for i in user_data[uid]["income"])
    expenses = sum(e[0] for e in user_data[uid]["expenses"])
    await message.answer(f"📈 Доходы: <b>{income} ₽</b>
📉 Расходы: <b>{expenses} ₽</b>")

@dp.message(F.text == "💰 Остаток")
async def show_balance(message: Message):
    uid = message.from_user.id
    income = sum(i[0] for i in user_data[uid]["income"])
    expenses = sum(e[0] for e in user_data[uid]["expenses"])
    balance = income - expenses
    await message.answer(f"💼 Остаток: <b>{balance} ₽</b>")

@dp.message(F.text == "📂 По категориям")
async def category_stats(message: Message):
    uid = message.from_user.id
    stats = defaultdict(int)
    for amount, _, cat in user_data[uid]["expenses"]:
        stats[cat] += amount
    lines = [f"📊 <b>{cat.capitalize()}:</b> {total} ₽" for cat, total in stats.items()]
    await message.answer("\n".join(lines) or "Нет расходов.")

@dp.message(F.text == "🗂 Категории")
async def edit_categories(message: Message, state: FSMContext):
    uid = message.from_user.id
    categories = user_data[uid]["categories"]
    text = "<b>📂 Текущие категории:</b>"
    for cat, words in categories.items():
        text += f"\n• <b>{cat}</b>: {', '.join(words) if words else '—'}"
    text += "\n\nВведите в формате:
<code>транспорт, стоянка, бензин, ремонт</code>"
    await message.answer(text)
    await state.set_state(CategoryState.editing)

@dp.message(CategoryState.editing)
async def save_category(message: Message, state: FSMContext):
    try:
        parts = [p.strip() for p in message.text.split(",")]
        category, *keywords = parts
        uid = message.from_user.id
        user_data[uid]["categories"][category.lower()] = [k.lower() for k in keywords]
        await message.answer(f"✅ Категория <b>{category}</b> обновлена.")
    except Exception:
        await message.answer("❗️ Неверный формат. Попробуйте:
<code>транспорт, бензин, ремонт</code>")
    await state.clear()

async def on_startup(app):
    webhook_url = f"{BASE_WEBHOOK_URL}{WEBHOOK_PATH}"
    await bot.set_webhook(webhook_url)
    print(f"✅ Webhook установлен: {webhook_url}")

async def on_shutdown(app):
    await bot.delete_webhook()

async def handle(request):
    body = await request.text()
    update = bot._parser.parse(body)
    await dp.feed_update(bot, update)
    return web.Response()

app = web.Application()
app.add_routes([web.post(WEBHOOK_PATH, handle)])
app.on_startup.append(on_startup)
app.on_shutdown.append(on_shutdown)

if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    web.run_app(app, host="0.0.0.0", port=PORT)
