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
WEBHOOK_HOST = os.getenv("WEBHOOK_HOST", "https://your-domain.com")
WEBHOOK_PATH = f"/webhook/{API_TOKEN}"
WEBHOOK_URL = f"{WEBHOOK_HOST}{WEBHOOK_PATH}"

# Инициализация бота
bot = Bot(
    token=API_TOKEN,
    default=DefaultBotProperties(parse_mode=ParseMode.HTML)
)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Словарь для хранения данных
user_data = {}

class AddCategoryState(StatesGroup):
    waiting_for_category = State()

def initialize_user_data(user_id):
    if user_id not in user_data:
        user_data[user_id] = {
            "income": [],
            "expenses": [],
            "categories": {
                "еда": ["еда", "продукты", "магазин"],
                "транспорт": ["метро", "такси", "автобус"],
                "развлечения": ["кино", "игры", "бар"],
                "прочее": []
            }
        }

# [Ваши обработчики сообщений здесь...]

async def on_startup(app: web.Application):
    await bot.set_webhook(WEBHOOK_URL)
    logger.info("Webhook установлен")

async def on_shutdown(app: web.Application):
    await bot.delete_webhook()
    logger.info("Webhook удален")

async def handle_webhook(request):
    if request.match_info.get('token') == API_TOKEN:
        update = types.Update(**(await request.json()))
        await dp.feed_update(bot=bot, update=update)
        return web.Response()
    return web.Response(status=403)

def main():
    app = web.Application()
    app.router.add_post(WEBHOOK_PATH, handle_webhook)
    app.on_startup.append(on_startup)
    app.on_shutdown.append(on_shutdown)
    
    web.run_app(
        app,
        host='0.0.0.0',
        port=int(os.getenv("PORT", 3000))
        
if __name__ == '__main__':
    main()
