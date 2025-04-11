from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart
from aiogram.types import Message
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from collections import defaultdict
import asyncio
import os
import re

API_TOKEN = os.getenv("API_TOKEN")
bot = Bot(token=API_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher(storage=MemoryStorage())

# Состояния
class CategoryState(StatesGroup):
    editing_category = State()

# Хранилище
user_data = defaultdict(lambda: {"categories": {
    "еда": ["еда", "продукты"],
    "транспорт": ["метро", "такси", "автобус"],
    "развлечения": ["кино", "игры", "бар"],
    "прочее": []
}})

@dp.message(F.text == "🗂 Категории")
async def edit_categories(message: Message, state: FSMContext):
    user_id = message.from_user.id
    cats = user_data[user_id]["categories"]
    text = "📂 Текущие категории:
"
    for cat, keys in cats.items():
        text += f"• {cat}: {', '.join(keys) if keys else '—'}\n"
    await message.answer(text)
    await message.answer(
        "✏️ Введите новую категорию и ключевые слова через запятую.\nПример:\nтранспорт, стоянка, бензин, автомойка, авто"
    )
    await state.set_state(CategoryState.editing_category)

@dp.message(CategoryState.editing_category)
async def save_category(message: Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text
    try:
        parts = [p.strip().lower() for p in text.split(",")]
        category = parts[0]
        keywords = parts[1:]
        user_data[user_id]["categories"][category] = keywords
        await message.answer(f"✅ Категория '{category}' добавлена/обновлена.")
    except Exception:
        await message.answer("❗ Ошибка. Формат: категория, ключевое слово1, ключевое слово2")
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())