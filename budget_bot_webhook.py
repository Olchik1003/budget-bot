import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode
from aiogram.utils import executor
from aiogram.types import Message
import os

API_TOKEN = os.getenv("API_TOKEN")
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Словарь для хранения данных о пользователях
user_data = {}

# Состояния и команды
@dp.message_handler(commands=['start'])
async def send_welcome(message: Message):
    user_id = message.from_user.id
    user_data[user_id] = {"income": [], "expenses": [], "categories": {"еда": ["еда", "продукты"], "транспорт": ["метро", "такси", "автобус"], "развлечения": ["кино", "игры", "бар"], "прочее": []}}
    
    await message.answer(
        "👋 Привет! Я бот для учёта бюджета. Просто отправь сообщение, например:\n"
        "+50000 зарплата\n"
        "1200 метро"
    )

@dp.message_handler(commands=['категории'])
async def show_categories(message: Message):
    user_id = message.from_user.id
    categories = user_data[user_id]["categories"]
    
    text = "📂 Текущие категории:\n"
    for category, keywords in categories.items():
        text += f"• {category}: {', '.join(keywords)}\n"
    
    await message.answer(text)

@dp.message_handler(commands=['добавитькатегорию'])
async def add_category(message: Message):
    await message.answer("💼 Введите новую категорию и ключевые слова через запятую. Пример: транспорт, метро, такси, автобус")

@dp.message_handler()
async def handle_message(message: Message):
    user_id = message.from_user.id
    text = message.text.strip()
    
    if text.startswith('+'):
        # Это доход
        try:
            amount, description = text.split(" ", 1)
            amount = int(amount.replace('+', '').strip())
            user_data[user_id]["income"].append((amount, description))
            await message.answer(f"Доход {amount} ₽ добавлен: {description}")
        except:
            await message.answer("❗ Неверный формат дохода. Используйте формат: +50000 зарплата")
    
    elif text.isdigit():
        # Это расход
        try:
            amount = int(text)
            category = "прочее"
            for cat, keywords in user_data[user_id]["categories"].items():
                if any(keyword in message.text.lower() for keyword in keywords):
                    category = cat
                    break
            user_data[user_id]["expenses"].append((amount, category))
            await message.answer(f"Расход {amount} ₽ добавлен в категорию: {category}")
        except:
            await message.answer("❗ Неверный формат расхода. Используйте формат: 1000 корм для кошки")
    
    else:
        await message.answer("❗ Неверный формат. Попробуйте использовать команды /категории или /добавитькатегорию")

# Запуск бота
if __name__ == '__main__':
    from aiogram import executor
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp, skip_updates=True)
