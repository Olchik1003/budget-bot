import asyncio
import logging
import os
from aiohttp import web
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.webhook.aiohttp_server import SimpleRequestHandler, setup_application
from aiogram.client.default import DefaultBotProperties
from collections import defaultdict

API_TOKEN = os.getenv("API_TOKEN")
WEBHOOK_PATH = f"/webhook/{API_TOKEN}"
WEBHOOK_URL = "https://budget-bot-8lfi.onrender.com" + WEBHOOK_PATH

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
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

@dp.message(CommandStart())
async def start(message: Message):
    user_data[message.from_user.id]["categories"] = default_categories.copy()
    await message.answer(
        """👋 Привет! Я бот для учёта бюджета.
Просто отправь сообщение, например:

<code>+50000 зарплата</code>
<code>1200 метро</code>""", reply_markup=main_kb
    )

@dp.message(Command("help"))
async def help_command(message: Message):
    await message.answer(
        "🆘 <b>Помощь по использованию бота</b>\n\n"
        "Вот что я умею:\n"
        "➕ <b>Доход</b> — <code>+50000 зарплата</code>\n"
        "💸 <b>Расход</b> — <code>200 кафе</code>\n"
        "📈 <b>Статистика</b>, 💰 <b>Остаток</b>, 📊 <b>По категориям</b>\n"
        "📝 <b>Категории</b> — <code>название, ключевое1, ключевое2</code>\n"
        "❌ <b>Удалить запись</b> — пока не реализовано\n\n"
        "ℹ️ Я сам определяю категории по ключевым словам.",
        parse_mode="HTML"
    )

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