import logging
from aiogram import Bot, Dispatcher, types, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import os
from aiohttp import web

# Настройка логгирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Конфигурация бота
API_TOKEN = os.getenv("API_TOKEN")
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "https://your-service-name.onrender.com")  # Замените на ваш URL
WEBHOOK_PATH = f"/webhook/{API_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# Инициализация бота
bot = Bot(
    token=API_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Словарь для хранения данных
user_data = {}

class AddCategoryState(StatesGroup):
    waiting_for_category = State()

def initialize_user_data(user_id):
    """Инициализация данных пользователя"""
    if user_id not in user_data:
        user_data[user_id] = {
            "income": [],
            "expenses": [],
            "categories": {
                "еда": ["еда", "продукты"],
                "транспорт": ["метро", "такси"],
                "развлечения": ["кино", "бар"],
                "прочее": []
            }
        }

@dp.message(F.text.lower().in_(["/start", "/help"]))
async def send_welcome(message: types.Message):
    """Обработка команд /start и /help"""
    initialize_user_data(message.from_user.id)
    await message.answer(
        "📊 Бот для учета бюджета\n\n"
        "Добавить доход: +5000 зарплата\n"
        "Добавить расход: 1500 продукты\n\n"
        "Команды:\n"
        "/категории - список категорий\n"
        "/добавитькатегорию - новая категория"
    )

@dp.message(F.text.lower() == "/категории")
async def show_categories(message: types.Message):
    """Показать категории"""
    user_id = message.from_user.id
    initialize_user_data(user_id)
    
    categories = "\n".join(
        f"• {cat}: {', '.join(keywords)}"
        for cat, keywords in user_data[user_id]["categories"].items()
    )
    await message.answer(f"📂 Категории:\n\n{categories}")

@dp.message(F.text.lower() == "/добавитькатегорию")
async def add_category_command(message: types.Message, state: FSMContext):
    """Начало добавления категории"""
    await state.set_state(AddCategoryState.waiting_for_category)
    await message.answer("Введите название категории и ключевые слова через запятую:")

@dp.message(AddCategoryState.waiting_for_category)
async def process_category(message: types.Message, state: FSMContext):
    """Обработка новой категории"""
    user_id = message.from_user.id
    parts = [p.strip() for p in message.text.split(",") if p.strip()]
    
    if len(parts) < 2:
        await message.answer("Нужно название и хотя бы одно ключевое слово")
        return
    
    category, *keywords = parts
    user_data[user_id]["categories"][category.lower()] = [k.lower() for k in keywords]
    await message.answer(f"✅ Категория '{category}' добавлена")
    await state.clear()

@dp.message(F.text.startswith("+"))
async def add_income(message: types.Message):
    """Добавление дохода"""
    try:
        amount = int(message.text.split()[0][1:])
        user_id = message.from_user.id
        initialize_user_data(user_id)
        user_data[user_id]["income"].append(amount)
        await message.answer(f"✅ Доход +{amount}₽ добавлен")
    except:
        await message.answer("❌ Формат: +5000 зарплата")

@dp.message(F.text[0].isdigit())
async def add_expense(message: types.Message):
    """Добавление расхода"""
    try:
        amount = int(message.text.split()[0])
        user_id = message.from_user.id
        initialize_user_data(user_id)
        category = "прочее"
        
        if len(message.text.split()) > 1:
            description = message.text.split()[1].lower()
            for cat, keywords in user_data[user_id]["categories"].items():
                if any(kw in description for kw in keywords):
                    category = cat
                    break
        
        user_data[user_id]["expenses"].append((amount, category))
        await message.answer(f"✅ Расход {amount}₽ ({category}) добавлен")
    except:
        await message.answer("❌ Формат: 1500 продукты")

async def on_startup(app: web.Application):
    """Действия при запуске"""
    await bot.set_webhook(WEBHOOK_URL)
    logger.info(f"Webhook установлен на {WEBHOOK_URL}")

async def on_shutdown(app: web.Application):
    """Действия при остановке"""
    await bot.delete_webhook()
    logger.info("Webhook удален")

async def webhook_handler(request):
    """Обработчик вебхука"""
    if request.match_info.get("token") == API_TOKEN:
        data = await request.json()
        update = types.Update(**data)
        await dp.feed_update(bot=bot, update=update)
        return web.Response()
    return web.Response(status=403)

def main():
    """Основная функция"""
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, webhook_handler)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    
    web.run_app(
        app,
        host="0.0.0.0",
        port=int(os.getenv("PORT", 3000))
    )

if __name__ == "__main__":
    main()
