import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.enums import ParseMode
import os
from aiohttp import web

# Настройка логгирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация бота
API_TOKEN = os.getenv("API_TOKEN")
WEBHOOK_HOST = 'https://your-domain.com'  # Замените на ваш домен
WEBHOOK_PATH = '/webhook/' + API_TOKEN
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN, parse_mode=ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Словарь для хранения данных о пользователях
user_data = {}

class AddCategoryState(StatesGroup):
    waiting_for_category = State()

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

@dp.message(F.text.lower() == '/start')
@dp.message(F.text.lower() == '/help')
async def send_welcome(message: types.Message):
    """Обработчик команд /start и /help"""
    user_id = message.from_user.id
    initialize_user_data(user_id)
    
    help_text = """
<b>💰 Бот для учета бюджета</b>

<b>Добавить доход:</b>
+50000 зарплата
+3000 подарок

<b>Добавить расход:</b>
1500 метро
2500 продукты
3000 кино

<b>📋 Доступные команды:</b>
/категории - показать все категории расходов
/добавитькатегорию - добавить новую категорию
/статистика - показать статистику (скоро)
"""
    await message.answer(help_text)

@dp.message(F.text.lower() == '/категории')
async def show_categories(message: types.Message):
    """Показать все категории расходов"""
    user_id = message.from_user.id
    initialize_user_data(user_id)
    
    categories = user_data[user_id]["categories"]
    
    text = "<b>📂 Ваши категории расходов:</b>\n\n"
    for category, keywords in categories.items():
        text += f"<b>• {category.capitalize()}</b>: {', '.join(keywords)}\n"
    
    await message.answer(text)

@dp.message(F.text.lower() == '/добавитькатегорию')
async def add_category_command(message: types.Message, state: FSMContext):
    """Начать процесс добавления новой категории"""
    await state.set_state(AddCategoryState.waiting_for_category)
    await message.answer(
        "Введите название новой категории и ключевые слова через запятую.\n"
        "Пример: <i>транспорт, метро, такси, автобус</i>"
    )

@dp.message(AddCategoryState.waiting_for_category)
async def process_category_name(message: types.Message, state: FSMContext):
    """Обработка ввода новой категории"""
    user_id = message.from_user.id
    initialize_user_data(user_id)
    
    input_text = message.text.strip().lower()
    parts = [part.strip() for part in input_text.split(',') if part.strip()]
    
    if len(parts) < 2:
        await message.answer("❗ Пожалуйста, укажите название категории и хотя бы одно ключевое слово.")
        return
    
    category_name = parts[0]
    keywords = parts[1:]
    
    if category_name in user_data[user_id]["categories"]:
        await message.answer(f"❗ Категория '{category_name}' уже существует!")
        await state.clear()
        return
    
    user_data[user_id]["categories"][category_name] = keywords
    await message.answer(
        f"✅ Категория <b>{category_name}</b> успешно добавлена с ключевыми словами: "
        f"{', '.join(keywords)}"
    )
    await state.clear()

@dp.message()
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
            await message.answer(
                f"✅ Доход <b>{amount} ₽</b> добавлен: <i>{description}</i>"
            )
        
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
            await message.answer(
                f"✅ Расход <b>{amount} ₽</b> добавлен в категорию: <b>{category}</b>"
            )
        
        else:
            await message.answer(
                "❗ Не понимаю ваш запрос. Введите доход (начинается с +) или расход (число).\n"
                "Используйте /help для справки."
            )
    
    except ValueError as e:
        await message.answer(
            f"❗ Ошибка: {e}\nПожалуйста, используйте правильный формат:\n"
            "Доход: +50000 зарплата\nРасход: 1500 метро"
        )
    except Exception as e:
        logger.error(f"Error processing message: {e}")
        await message.answer("❗ Произошла ошибка при обработке вашего сообщения. Пожалуйста, попробуйте еще раз.")

async def on_startup(bot: Bot):
    """Действия при запуске бота"""
    await bot.set_webhook(WEBHOOK_URL)
    logger.info("Бот запущен")

async def on_shutdown(bot: Bot):
    """Действия при остановке бота"""
    logger.warning('Выключение..')
    await bot.delete_webhook()
    logger.warning('Бот выключен')

async def handle_webhook(request):
    """Обработчик вебхука"""
    if request.match_info.get('token') == API_TOKEN:
        update = types.Update(**(await request.json()))
        await dp.feed_update(bot=bot, update=update)
        return web.Response()
    return web.Response(status=403)

def main():
    """Основная функция для запуска приложения"""
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, handle_webhook)
    
    # Настройка вебхука при запуске
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    
    web.run_app(
        app,
        host='0.0.0.0',
        port=os.getenv("PORT", 3000)
    )

if __name__ == '__main__':
    main()
