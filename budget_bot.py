import asyncio
import logging
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.types import Message, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from collections import defaultdict
import re

# Инициализация бота
import os
API_TOKEN = os.getenv("API_TOKEN")
bot = Bot(token=API_TOKEN)
dp = Dispatcher(storage=MemoryStorage())

# Временное хранилище данных
user_data = defaultdict(lambda: {"income": [], "expenses": [], "categories": {}})

# Клавиатура
main_kb = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📈 Статистика")],
        [KeyboardButton(text="➕ Доход"), KeyboardButton(text="💸 Расход")],
        [KeyboardButton(text="📊 По категориям"), KeyboardButton(text="💰 Остаток")],
        [KeyboardButton(text="📝 Категории"), KeyboardButton(text="❌ Удалить запись")],
    ],
    resize_keyboard=True
)

# Категории по умолчанию
default_categories = {
    "еда": ["еда", "продукты"],
    "животные": ["корм", "кот", "собака", "животные"],
    "транспорт": ["метро", "автобус", "транспорт"],
    "развлечения": ["кино", "развлечения", "игры"],
    "прочее": []
}

# Состояния FSM
class ExpenseState(StatesGroup):
    waiting_for_expense = State()

class IncomeState(StatesGroup):
    waiting_for_income = State()

class CategoryState(StatesGroup):
    editing_category = State()

class DeleteState(StatesGroup):
    choosing_delete = State()

# Обработчики
@dp.message(CommandStart())
async def start(message: Message):
    user_id = message.from_user.id
    user_data[user_id]["categories"] = default_categories.copy()
    await message.answer("🎉 Добро пожаловать в бот учёта бюджета! 📊\nГотов начать работу 💼", reply_markup=main_kb)

@dp.message(F.text == "➕ Доход")
async def income_start(message: Message, state: FSMContext):
    await message.answer("💰 Введите сумму дохода с описанием (необязательно), например: +50000 зарплата")
    await state.set_state(IncomeState.waiting_for_income)

@dp.message(IncomeState.waiting_for_income)
async def add_income(message: Message, state: FSMContext):
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
async def expense_start(message: Message, state: FSMContext):
    await message.answer("🧾 Введите расход: сумму и назначение, например: 1000 корм для кошки")
    await state.set_state(ExpenseState.waiting_for_expense)

@dp.message(ExpenseState.waiting_for_expense)
async def add_expense(message: Message, state: FSMContext):
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
async def show_stats(message: Message):
    user_id = message.from_user.id
    total_income = sum(i[0] for i in user_data[user_id]["income"])
    total_expenses = sum(e[0] for e in user_data[user_id]["expenses"])
    await message.answer(f"📊 Всего доходов: {total_income} ₽\n📉 Всего расходов: {total_expenses} ₽")

@dp.message(F.text == "📊 По категориям")
async def category_stats(message: Message):
    user_id = message.from_user.id
    stats = defaultdict(int)
    for amount, _, category in user_data[user_id]["expenses"]:
        stats[category] += amount
    text = "📁 Статистика по категориям:\n"
    for cat, total in stats.items():
        text += f"🔸 {cat.capitalize()}: {total} ₽\n"
    await message.answer(text)

@dp.message(F.text == "💰 Остаток")
async def balance(message: Message):
    user_id = message.from_user.id
    income = sum(i[0] for i in user_data[user_id]["income"])
    expenses = sum(e[0] for e in user_data[user_id]["expenses"])
    await message.answer(f"💼 Текущий баланс: {income - expenses} ₽")

@dp.message(F.text == "📝 Категории")
async def edit_categories(message: Message, state: FSMContext):
    await message.answer("🧠 Введите новую категорию и ключевые слова через запятую\nПример: техника, телефон, ноутбук")
    await state.set_state(CategoryState.editing_category)

@dp.message(CategoryState.editing_category)
async def save_category(message: Message, state: FSMContext):
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

@dp.message(F.text == "❌ Удалить запись")
async def delete_entry_prompt(message: Message, state: FSMContext):
    await message.answer("🗑 Введите 'доход N' или 'расход N', где N — номер записи (счёт от последней)")
    await state.set_state(DeleteState.choosing_delete)

@dp.message(DeleteState.choosing_delete)
async def delete_entry(message: Message, state: FSMContext):
    user_id = message.from_user.id
    text = message.text.lower()
    if text.startswith("доход"):
        try:
            index = int(text.split()[1]) - 1
            entry = user_data[user_id]["income"].pop(-1 - index)
            await message.answer(f"❌ Удалён доход: {entry[0]} ₽ — {entry[1]}")
        except:
            await message.answer("⚠️ Не удалось удалить доход. Проверь номер.")
    elif text.startswith("расход"):
        try:
            index = int(text.split()[1]) - 1
            entry = user_data[user_id]["expenses"].pop(-1 - index)
            await message.answer(f"❌ Удалён расход: {entry[0]} ₽ — {entry[1]} ({entry[2]})")
        except:
            await message.answer("⚠️ Не удалось удалить расход. Проверь номер.")
    else:
        await message.answer("Формат: 'доход 1' или 'расход 1'")
    await state.clear()

async def main():
    logging.basicConfig(level=logging.INFO)
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
