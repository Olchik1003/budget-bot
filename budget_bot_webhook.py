import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import os

API_TOKEN = os.getenv("API_TOKEN")
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Словарь для хранения данных о пользователях
user_data = {}

# Состояния и команды
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    user_id = message.from_user.id
    user_data[user_id] = {"income": [], "expenses": [], "categories": {"еда": ["еда", "продукты"], "транспорт": ["метро", "такси", "автобус"], "развлечения": ["кино", "игры", "бар"], "прочее": []}}
    
    await message.answer(
        '''Привет! Я бот для учёта бюджета. Просто отправь сообщение, например:

+50000 зарплата
1200 метро''', parse_mode="HTML"
    )

@dp.message_handler(commands=['категории'])
async def show_categories(message: types.Message):
    user_id = message.from_user.id
    categories = user_data[user_id]["categories"]
    
    text = '''Текущие категории:
'''
    for category, keywords in categories.items():
        text += f"* {category}: {', '.join(keywords)}n"
    
    await message.answer(text, parse_mode="HTML")

@dp.message_handler(commands=['добавитькатегорию'])
async def add_category(message: types.Message):
    await message.answer("Введите новую категорию и ключевые слова через запятую. Пример: транспорт, метро, такси, автобус", parse_mode="HTML")

@dp.message_handler()
async def handle_message(message: types.Message):
    user_id = message.from_user.id
    text = message.text.strip()
    
    if text.startswith('+'):
        # Это доход
        try:
            amount, description = text.split(" ", 1)
            amount = int(amount.replace('+', '').strip())
            user_data[user_id]["income"].append((amount, description))
            await message.answer(f"Доход {amount} ₽ добавлен: {description}", parse_mode="HTML")
        except:
            await message.answer("❗ Неверный формат дохода. Используйте формат: +50000 зарплата", parse_mode="HTML")
    
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
            await message.answer(f"Расход {amount} ₽ добавлен в категорию: {category}", parse_mode="HTML")
        except:
            await message.answer("❗ Неверный формат расхода. Используйте формат: 1000 корм для кошки", parse_mode="HTML")
    
    else:
        await message.answer("❗ Неверный формат. Попробуйте использовать команды /категории или /добавитькатегорию", parse_mode="HTML")

# Запуск бота
if __name__ == '__main__':
    from aiogram import executor
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp, skip_updates=True)
