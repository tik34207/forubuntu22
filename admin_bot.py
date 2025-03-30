import logging
import os
from aiogram import Bot, Dispatcher, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from config import ADMIN_API_TOKEN, ADMIN_IDS
import database as db
from keyboards import (
    get_admin_main_keyboard, get_users_page_keyboard,
    get_user_manage_keyboard
)

logging.basicConfig(level=logging.INFO)

bot = Bot(token=ADMIN_API_TOKEN)
storage = MemoryStorage()
dp_admin = Dispatcher(bot, storage=storage)
dp_admin.middleware.setup(LoggingMiddleware())

class AdminStates(StatesGroup):
    awaiting_admin_id = State()


def is_admin(user_id):
    return user_id in ADMIN_IDS

@dp_admin.message_handler(commands=['start'])
async def admin_start(message: types.Message):
    if not is_admin(message.from_user.id):
        return await message.reply("Нет доступа.")
    users = db.get_all_users()
    await message.answer("Выберите действие:", reply_markup=get_admin_main_keyboard(len(users)))

@dp_admin.callback_query_handler(lambda c: c.data == "manage_users")
async def handle_manage_users(call: types.CallbackQuery):
    users = db.get_all_users()
    page = 0
    per_page = 10
    total_pages = (len(users) + per_page - 1) // per_page
    page_users = users[page * per_page:(page + 1) * per_page]
    await call.message.edit_text("Список пользователей:", reply_markup=get_users_page_keyboard(page_users, page, total_pages))

@dp_admin.callback_query_handler(lambda c: c.data.startswith("page_"))
async def paginate_users(call: types.CallbackQuery):
    page = int(call.data.split("_")[1])
    users = db.get_all_users()
    per_page = 10
    total_pages = (len(users) + per_page - 1) // per_page
    page_users = users[page * per_page:(page + 1) * per_page]
    await call.message.edit_text("Список пользователей:", reply_markup=get_users_page_keyboard(page_users, page, total_pages))

@dp_admin.callback_query_handler(lambda c: c.data.startswith("user_"))
async def handle_user_select(call: types.CallbackQuery):
    user_id = int(call.data.split("_")[1])
    users = db.get_all_users()
    user_info = next((u for u in users if u[0] == user_id), None)
    if user_info:
        is_banned = bool(user_info[2])
        await call.message.edit_text(
            f"Управление пользователем {user_info[1] or user_info[0]}:",
            reply_markup=get_user_manage_keyboard(user_id, is_banned)
        )

@dp_admin.callback_query_handler(lambda c: c.data.startswith("ban_") or c.data.startswith("unban_"))
async def toggle_ban(call: types.CallbackQuery):
    parts = call.data.split("_")
    user_id = int(parts[1])
    banned = parts[0] == "ban"
    db.set_ban_status(user_id, banned)
    await call.answer("✅ Статус обновлен")
    users = db.get_all_users()
    user_info = next((u for u in users if u[0] == user_id), None)
    if user_info:
        await call.message.edit_reply_markup(reply_markup=get_user_manage_keyboard(user_id, banned))

@dp_admin.callback_query_handler(lambda c: c.data.startswith("accounts_"))
async def show_user_accounts(call: types.CallbackQuery):
    user_id = int(call.data.split("_")[1])
    accounts = db.get_accounts_by_user(user_id)
    if not accounts:
        return await call.answer("Аккаунты не найдены", show_alert=True)

    country_accounts = {}
    for country, acc in accounts:
        country_accounts.setdefault(country, []).append(acc)

    filename = f"accounts_{user_id}.txt"
    with open(filename, "w", encoding="utf-8") as f:
        for country, accs in country_accounts.items():
            f.write(f"{country}:\n")
            for a in accs:
                f.write(f"{a}\n")
            f.write("\n")

    await bot.send_document(call.from_user.id, types.InputFile(filename))
    os.remove(filename)

if __name__ == '__main__':
    from aiogram import executor
    from database import init_db
    init_db()
    executor.start_polling(dp_admin, skip_updates=True)
