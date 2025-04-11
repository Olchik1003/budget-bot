import asyncio
import logging
import os
import re
from collections import defaultdict, Counter
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
import matplotlib.pyplot as plt

API_TOKEN = os.getenv("API_TOKEN")
WEBHOOK_PATH = f"/webhook/{API_TOKEN}"
PORT = int(os.getenv("PORT", 10000))
BASE_WEBHOOK_URL = os.getenv("RENDER_EXTERNAL_URL")

bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

user_data = defaultdict(lambda: {
    "income": [],
    "expenses": [],
    "categories": {
        "еда": ["еда", "продукты"],
        "транспорт": ["метро", "такси", "автобус"],
        "развлечения": ["кино", "игры", "бар"],
        "прочее": []
    }
})

main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📊 Статистика"), KeyboardButton(text="💰 Остаток")],
        [KeyboardButton(text="📂 Категории"), KeyboardButton(text="📈 По категориям")]
    ],
    resize_keyboard=True
)

class EditCategory(StatesGroup):
    waiting_input = State()

@dp.message(CommandStart())
async def start(message: Message):
    await message.answer(
        """👋 Привет! Я бот для учёта бюджета.
Просто отправь сообщение, например:

<code>+50000 зарплата</code>
<code>1200 метро</code>""",
        reply_markup=main_kb
    )

@dp.message(F.text == "📂 Категории")
async def show_categories(message: Message, state: FSMContext):
    user_id = message.from_user.id
    cats = user_data[user_id]["categories"]
    text = "📂 Текущие категории:
"
    for cat, keys in cats.items():
        text += f"• <b>{cat}</b>: {', '.join(keys)}
"
    text += "
Отправьте новую категорию в формате:
<code>транспорт, авто, бензин, стоянка</code>"
    await state.set_state(EditCategory.waiting_input)
    await message.answer(text)

@dp.message(EditCategory.waiting_input)
async def save_category(message: Message, state: FSMContext):
    user_id = message.from_user.id
    try:
        parts = message.text.split(",")
        category = parts[0].strip()
        keywords = [p.strip().lower() for p in parts[1:]]
        user_data[user_id]["categories"][category] = keywords
        await message.answer(f"✅ Категория <b>{category}</b> обновлена.")
    except:
        await message.answer("❗️ Неверный формат. Используйте:
<code>еда, продукты, супермаркет</code>")
    await state.clear()

@dp.message(F.text == "📊 Статистика")
async def stats(message: Message):
    user_id = message.from_user.id
    income = sum(i[0] for i in user_data[user_id]["income"])
    expenses = sum(e[0] for e in user_data[user_id]["expenses"])
    await message.answer(f"📊 Доходы: {income} ₽
📉 Расходы: {expenses} ₽")

@dp.message(F.text == "💰 Остаток")
async def balance(message: Message):
    user_id = message.from_user.id
    income = sum(i[0] for i in user_data[user_id]["income"])
    expenses = sum(e[0] for e in user_data[user_id]["expenses"])
    await message.answer(f"💼 Остаток: {income - expenses} ₽")

@dp.message(F.text == "📈 По категориям")
async def by_category(message: Message):
    user_id = message.from_user.id
    counter = Counter()
    for amount, _, cat in user_data[user_id]["expenses"]:
        counter[cat] += amount
    if not counter:
        await message.answer("Нет расходов по категориям.")
        return
    # Построим круговую диаграмму
    labels, values = zip(*counter.items())
    plt.figure()
    plt.pie(values, labels=labels, autopct="%1.1f%%")
    plt.title("Расходы по категориям")
    path = "/tmp/pie.png"
    plt.savefig(path)
    plt.close()
    with open(path, "rb") as f:
        await message.answer_photo(f)

@dp.message()
async def parse_text(message: Message):
    user_id = message.from_user.id
    text = message.text.strip()
    if text.startswith("+"):
        match = re.match(r"\+(\d+)\s*(.*)", text)
        if match:
            amount = int(match.group(1))
            desc = match.group(2) or "Без описания"
            user_data[user_id]["income"].append((amount, desc))
            await message.answer(f"✅ Доход {amount} ₽ добавлен: {desc}")
        else:
            await message.answer("❗️ Неверный формат. Используйте:
<code>+50000 зарплата</code>")
    else:
        match = re.match(r"(\d+)\s*(.+)", text)
        if match:
            amount = int(match.group(1))
            desc = match.group(2)
            cats = user_data[user_id]["categories"]
            cat = "прочее"
            for c, keys in cats.items():
                if any(k in desc.lower() for k in keys):
                    cat = c
                    break
            user_data[user_id]["expenses"].append((amount, desc, cat))
            await message.answer(f"🔻 Расход {amount} ₽ добавлен: {desc} (категория: {cat})")
        else:
            await message.answer("❗️ Неверный формат. Используйте:
<code>1200 метро</code>")

async def on_startup(bot: Bot):
    webhook_url = BASE_WEBHOOK_URL + WEBHOOK_PATH
    await bot.set_webhook(webhook_url, drop_pending_updates=True)

async def main():
    logging.basicConfig(level=logging.INFO)
    app = web.Application()
    SimpleRequestHandler(dispatcher=dp, bot=bot).register(app, path=WEBHOOK_PATH)
    setup_application(app, dp, bot=bot)
    await on_startup(bot)
    web.run_app(app, host="0.0.0.0", port=PORT)

if __name__ == '__main__':
    asyncio.run(main())
