import logging
from aiogram import Bot, Dispatcher, types
from aiogram.utils import executor
import os

API_TOKEN = os.getenv("API_TOKEN")
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Словарь для хранения данных о пользователях
user_data = {}

def initialize_user_data(user_id):
    """Инициализирует данные пользователя при первом использовании"""
    if user_id not in user_data:
        user_data[user_id] = {
            "income": [],
            "expenses": [],
            "categories": {
                "еда": ["еда", "продукты", "магазин", "супермаркет"],
                "транспорт": ["метро", "такси", "автобус", "транспорт", "бензин"],
                "развлечения": ["кино", "игры", "бар", "ресторан", "кафе", "концерт"],
                "жилье": ["аренда", "коммуналка", "квартира", "дом"],
                "здоровье": ["аптека", "врач", "больница", "лекарства"],
                "прочее": []
            }
        }

@dp.message_handler(commands=['start', 'help'])
async def send_welcome(message: types.Message):
    """Обработчик команд /start и /help"""
    user_id = message.from_user.id
    initialize_user_data(user_id)
    
    help_text = """
Привет! Я бот для учёта бюджета. Вот что я умею:

<b>Добавить доход:</b>
+50000 зарплата
+3000 подарок

<b>Добавить расход:</b>
1500 метро
2500 продукты
3000 кино

<b>Команды:</b>
/категории - показать все категории расходов
/добавитькатегорию - добавить новую категорию
/статистика - показать статистику (скоро)
"""
    await message.answer(help_text, parse_mode="HTML")

@dp.message_handler(commands=['категории'])
async def show_categories(message: types.Message):
    """Показать все категории расходов"""
    user_id = message.from_user.id
    initialize_user_data(user_id)
    
    categories = user_data[user_id]["categories"]
    
    text = "<b>Ваши категории расходов:</b>\n\n"
    for category, keywords in categories.items():
        text += f"<b>{category.capitalize()}</b>: {', '.join(keywords)}\n"
    
    await message.answer(text, parse_mode="HTML")

@dp.message_handler(commands=['добавитькатегорию'])
async def add_category(message: types.Message):
    """Добавить новую категорию"""
    user_id = message.from_user.id
    initialize_user_data(user_id)
    
    # Получаем текст после команды
    command_parts = message.get_args().split(',')
    
    if len(command_parts) < 2:
        await message.answer("❗ Пожалуйста, укажите название категории и ключевые слова через запятую.\nПример: /добавитькатегорию транспорт, метро, такси, автобус")
        return
    
    category_name = command_parts[0].strip().lower()
    keywords = [kw.strip().lower() for kw in command_parts[1:]]
    
    if category_name in user_data[user_id]["categories"]:
        await message.answer(f"❗ Категория '{category_name}' уже существует!")
        return
    
    user_data[user_id]["categories"][category_name] = keywords
    await message.answer(f"✅ Категория '{category_name}' успешно добавлена с ключевыми словами: {', '.join(keywords)}")

@dp.message_handler()
async def handle_message(message: types.Message):
    """Обработчик всех текстовых сообщений"""
    user_id = message.from_user.id
    initialize_user_data(user_id)
    text = message.text.strip().lower()
    
    try:
        # Обработка дохода (начинается с +)
        if text.startswith('+'):
            parts = text.split(maxsplit=1)
            if len(parts) < 2:
                raise ValueError("Не указано описание дохода")
            
            amount = int(parts[0][1:].strip())
            description = parts[1].strip()
            
            user_data[user_id]["income"].append((amount, description))
            await message.answer(f"✅ Доход <b>{amount} ₽</b> добавлен: <i>{description}</i>", parse_mode="HTML")
        
        # Обработка расхода (число в начале)
        elif text[0].isdigit():
            parts = text.split(maxsplit=1)
            amount = int(parts[0].strip())
            
            # Определяем категорию по ключевым словам
            category = "прочее"
            description = ""
            
            if len(parts) > 1:
                description = parts[1].strip()
                for cat, keywords in user_data[user_id]["categories"].items():
                    if any(keyword in description for keyword in keywords):
                        category = cat
                        break
            
            user_data[user_id]["expenses"].append((amount, category, description))
            await message.answer(f"✅ Расход <b>{amount} ₽</b> добавлен в категорию: <b>{category}</b>", parse_mode="HTML")
        
        else:
            await message.answer("❗ Не понимаю ваш запрос. Введите доход (начинается с +) или расход (число).\nИспользуйте /help для справки.")
    
    except ValueError as e:
        await message.answer(f"❗ Ошибка: {e}\nПожалуйста, используйте правильный формат:\nДоход: +50000 зарплата\nРасход: 1500 метро")
    except Exception as e:
        logging.error(f"Error processing message: {e}")
        await message.answer("❗ Произошла ошибка при обработке вашего сообщения. Пожалуйста, попробуйте еще раз.")

if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    executor.start_polling(dp, skip_updates=True)
