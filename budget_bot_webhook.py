import asyncio
import logging
import os
import re
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from collections import defaultdict

API_TOKEN = os.getenv("API_TOKEN")
WEBHOOK_PATH = f"/webhook/{API_TOKEN}"
WEBHOOK_URL = "https://budget-bot-8lfi.onrender.com" + WEBHOOK_PATH

bot = Bot(token=API_TOKEN, parse_mode='HTML')
dp = Dispatcher(storage=MemoryStorage())

user_data = defaultdict(lambda: {"income": [], "expenses": [], "categories": {}})

main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📈 Статистика"), KeyboardButton(text="💰 Остаток")],
        [KeyboardButton(text="📊 По категориям"), KeyboardButton(text="📝 Категории")],
    ],
    resize_keyboard=True
)

default_categories = {
    "еда": ["еда", "продукты", "кафе", "ресторан"],
    "транспорт": ["метро", "такси", "бензин", "автобус"],
    "развлечения": ["кино", "игры", "развлечения"],
    "животные": ["корм", "кот", "собака", "ветеринар"],
    "прочее": []
}

class States(StatesGroup):
    waiting_text = State()

@dp.message(CommandStart())
async def start(message: Message):
    user_data[message.from_user.id]["categories"] = default_categories.copy()
    await message.answer("👋 Привет! Я бот для учёта бюджета. Просто отправь сообщение, например:

"
                         "<code>+50000 зарплата</code>
<code>1200 метро</code>",
                         reply_markup=main_kb)

@dp.message(Command("help"))
async def help_command(message: Message):
    await message.answer(
        "🆘 <b>Помощь по использованию бота</b>

"
        "Вот что я умею:
"
        "➕ <b>Доход</b> — добавление дохода. Например: <code>+50000 зарплата</code>
"
        "💸 <b>Расход</b> — добавление расхода. Например: <code>200 кафе</code>
"
        "📈 <b>Статистика</b> — вся статистика по доходам и расходам
"
        "📊 <b>По категориям</b> — расходы по категориям
"
        "💰 <b>Остаток</b> — текущий баланс
"
        "📝 <b>Категории</b> — задать свои категории расходов
"
        "❌ <b>Удалить запись</b> — удалить доход или расход

"
        "Также я автоматически определяю категорию расхода по ключевым словам.

"
        "ℹ️ Если возникли вопросы — пиши!",
        parse_mode="HTML"
    )

@dp.message(F.text)
async def handle_input(message: Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.strip()
    if re.match(r'^[+]?\d+', text):
        match = re.match(r'^([+]?\d+)\s+(.+)', text)
        if not match:
            await message.answer("❗ Пожалуйста, укажи сумму и описание.")
            return
        amount = int(match.group(1).replace("+", ""))
        desc = match.group(2)
        if text.startswith("+"):
            user_data[user_id]["income"].append((amount, desc))
            await message.answer(f"💰 Доход {amount} ₽ добавлен: {desc}")
        else:
            category = "прочее"
            for cat, keys in user_data[user_id]["categories"].items():
                if any(k in desc.lower() for k in keys):
                    category = cat
                    break
            user_data[user_id]["expenses"].append((amount, desc, category))
            await message.answer(f"💸 Расход {amount} ₽ добавлен: {desc} (категория: {category})")
    elif text.lower() == "остаток":
        income = sum(i[0] for i in user_data[user_id]["income"])
        expense = sum(e[0] for e in user_data[user_id]["expenses"])
        await message.answer(f"💼 Остаток: {income - expense} ₽")
    elif text.lower() in ["статистика", "📈 статистика"]:
        income = sum(i[0] for i in user_data[user_id]["income"])
        expense = sum(e[0] for e in user_data[user_id]["expenses"])
        await message.answer(f"📊 Доходы: {income} ₽\n📉 Расходы: {expense} ₽")
    elif text.lower() in ["по категориям", "📊 по категориям"]:
        stats = {}
        for amount, _, cat in user_data[user_id]["expenses"]:
            stats[cat] = stats.get(cat, 0) + amount
        if not stats:
            await message.answer("Нет расходов по категориям.")
        else:
            result = "📂 Расходы по категориям:\n"
            for cat, total in stats.items():
                result += f"• {cat}: {total} ₽\n"
            await message.answer(result)
    elif text.lower() in ["категории", "📝 категории"]:
        await message.answer("Напиши новую категорию в формате:
<code>название, ключевое1, ключевое2</code>")
        await state.set_state(States.waiting_text)
    else:
        await message.answer("❔ Не понял. Напиши <code>/help</code> для списка команд.")

@dp.message(States.waiting_text)
async def add_category(message: Message, state: FSMContext):
    user_id = message.from_user.id
    parts = message.text.split(",")
    category = parts[0].strip().lower()
    keywords = [p.strip().lower() for p in parts[1:]]
    user_data[user_id]["categories"][category] = keywords
    await message.answer(f"✅ Категория '{category}' добавлена.")
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