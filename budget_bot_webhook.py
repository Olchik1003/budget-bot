import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import ParseMode, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from collections import defaultdict
import re

API_TOKEN = '7654498035:AAEfTDuIVCXsQ7cccVmGDlfuEddoL3ZKDro'  # Ваш токен
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

user_data = defaultdict(lambda: {"income": [], "expenses": [], "categories": {}})

# Клавиатура
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📈 Статистика")],
        [KeyboardButton(text="➕ Доход"), KeyboardButton(text="💸 Расход")],
        [KeyboardButton(text="📊 По категориям"), KeyboardButton(text="💰 Остаток")],
        [KeyboardButton(text="📝 Категории")]
    ],
    resize_keyboard=True
)

default_categories = {
    "еда": ["еда", "продукты"],
    "животные": ["корм", "кот", "собака", "животные"],
    "транспорт": ["метро", "автобус", "такси"],
    "развлечения": ["кино", "игры"],
    "прочее": []
}

class ExpenseState(StatesGroup):
    waiting_for_expense = State()

class IncomeState(StatesGroup):
    waiting_for_income = State()

class CategoryState(StatesGroup):
    editing_category = State()

class DeleteState(StatesGroup):
    choosing_delete = State()

@dp.message(commands=['start'])
async def start(message: types.Message):
    user_id = message.from_user.id
    user_data[user_id]["categories"] = default_categories.copy()
    await message.answer("🎉 Добро пожаловать в бот учёта бюджета! 📊\nГотов начать работу 💼", reply_markup=main_kb)

@dp.message(F.text == "➕ Доход")
async def income_start(message: types.Message, state: FSMContext):
    await message.answer("💰 Введите сумму дохода с описанием (необязательно), например: +50000 зарплата")
    await state.set_state(IncomeState.waiting_for_income)

@dp.message(IncomeState.waiting_for_income)
async def add_income(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text
    match = re.match(r"[+]?([\d]+)(?:\s+(.+))?", text)
    if match:
        amount = int(match.group(1))
        description = match.group(2) or "Без описания"
        user_data[user_id]["income"].append((amount, description))
        await message.answer(f"✅ Доход {amount} ₽ добавлен: {description} 💼") 
    else:
        await message.answer("❗ Неверный формат. Попробуйте снова.")
    await state.clear()

@dp.message(F.text == "💸 Расход")
async def expense_start(message: types.Message, state: FSMContext):
    await message.answer("🧾 Введите расход: сумму и назначение, например: 1000 корм для кошки")
    await state.set_state(ExpenseState.waiting_for_expense)

@dp.message(ExpenseState.waiting_for_expense)
async def add_expense(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text
    match = re.match(r"(\d+)\s+(.+)", text)
    if match:
        amount = int(match.group(1))
        description = match.group(2)
        category = "прочее"
        for cat, keywords in user_data[user_id]["categories"].items():
            if any(keyword in description.lower() for keyword in keywords):
                category = cat
                break
        user_data[user_id]["expenses"].append((amount, description, category))
        await message.answer(f"🔻 Расход {amount} ₽ добавлен: {description} (категория: {category})") 
    else:
        await message.answer("❗ Неверный формат. Попробуйте снова.")
    await state.clear()

@dp.message(F.text == "📈 Статистика")
async def show_stats(message: types.Message):
    user_id = message.from_user.id
    total_income = sum(i[0] for i in user_data[user_id]["income"])
    total_expenses = sum(e[0] for e in user_data[user_id]["expenses"])
    await message.answer(f"📊 Всего доходов: {total_income} ₽\n📉 Всего расходов: {total_expenses} ₽")

@dp.message(F.text == "📊 По категориям")
async def category_stats(message: types.Message):
    user_id = message.from_user.id
    stats = defaultdict(int)
    for amount, _, category in user_data[user_id]["expenses"]:
        stats[category] += amount
    text = "📁 Статистика по категориям:\n"
    for cat, total in stats.items():
        text += f"🔸 {cat.capitalize()}: {total} ₽\n"
    await message.answer(text)

@dp.message(F.text == "💰 Остаток")
async def balance(message: types.Message):
    user_id = message.from_user.id
    income = sum(i[0] for i in user_data[user_id]["income"])
    expenses = sum(e[0] for e in user_data[user_id]["expenses"])
    await message.answer(f"💼 Текущий баланс: {income - expenses} ₽")

@dp.message(F.text == "📝 Категории")
async def edit_categories(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    categories = user_data[user_id]["categories"]
    text = "📂 Текущие категории:\n"
    for category, keywords in categories.items():
        text += f"• {category}: {', '.join(keywords)}\n"
    await message.answer(text + "\nВведите новую категорию и ключевые слова через запятую\nПример: техника, телефон, ноутбук")
    await state.set_state(CategoryState.editing_category)

@dp.message(CategoryState.editing_category)
async def save_category(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text
    try:
        parts = text.split(",")
        category = parts[0].strip()
        keywords = [p.strip().lower() for p in parts[1:]]
        user_data[user_id]["categories"][category] = keywords
        await message.answer(f"✅ Категория '{category}' добавлена/обновлена.")
    except:
        await message.answer("❗ Ошибка. Формат: категория, ключевое слово1, ключевое слово2")
    await state.clear()

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
