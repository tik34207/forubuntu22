from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
import database as db  # Добавляем импорт database
from aiogram import types

def get_users_page_keyboard(users, page, total_pages):
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    for user_id, username, banned in users:
        name = username or f"id:{user_id}"
        status = "✔" if not banned else "🚫"
        keyboard.add(types.InlineKeyboardButton(f"{name} {status}", callback_data=f"user_{user_id}"))

    nav_buttons = []
    if page > 0:
        nav_buttons.append(types.InlineKeyboardButton("⬅️", callback_data=f"page_{page - 1}"))
    if page < total_pages - 1:
        nav_buttons.append(types.InlineKeyboardButton("➡️", callback_data=f"page_{page + 1}"))

    if nav_buttons:
        keyboard.row(*nav_buttons)

    keyboard.add(types.InlineKeyboardButton("🔙Назад", callback_data="back_to_main"))
    return keyboard

def get_user_manage_keyboard(user_id, is_banned):
    keyboard = types.InlineKeyboardMarkup(row_width=2)
    toggle_text = "🚫 Забанить" if not is_banned else "✔ Разбанить"
    toggle_callback = f"ban_{user_id}" if not is_banned else f"unban_{user_id}"
    keyboard.add(
        types.InlineKeyboardButton(toggle_text, callback_data=toggle_callback),
        types.InlineKeyboardButton("📂 Аккаунты", callback_data=f"accounts_{user_id}")
    )
    keyboard.add(types.InlineKeyboardButton("🔙Назад", callback_data="manage_users"))
    return keyboard

def get_main_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton('🛠️Управление аккаунтами', callback_data='manage_accounts'),
        InlineKeyboardButton('🔑Мои аккаунты', callback_data='my_accounts'),
        InlineKeyboardButton('📩Получить код', callback_data='get_code'),
        InlineKeyboardButton('🌎Управление странами', callback_data='manage_countries'),
        InlineKeyboardButton('🌆Уникализация', callback_data='unique')
    )
    return markup

def get_account_management_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton('➕Добавить аккаунты', callback_data='add_accounts'),
        InlineKeyboardButton('➖Получить аккаунты', callback_data='get_accounts'),
        InlineKeyboardButton('🔙Назад', callback_data='back_to_main')
    )
    return markup

def get_my_accounts_keyboard(user_id):
    accounts = db.get_stats(user_id)
    response = "Мои аккаунты:\n"
    for country, count in accounts:
        response += f"{country} - {count}\n"
    return response

def get_country_keyboard(user_id):
    countries = db.get_countries(user_id)
    markup = InlineKeyboardMarkup(row_width=2)
    for country in countries:
        markup.add(InlineKeyboardButton(country[0], callback_data=f"country_{country[0]}"))
    markup.add(InlineKeyboardButton('🔙Назад', callback_data='back_to_main'))
    return markup

def get_country_management_keyboard(user_id):
    countries = db.get_countries(user_id)
    markup = InlineKeyboardMarkup(row_width=2)
    for country in countries:
        markup.add(InlineKeyboardButton(country[0], callback_data=f"manage_country_{country[0]}"))
    markup.add(InlineKeyboardButton('➕Добавить страну', callback_data='new_country'))
    markup.add(InlineKeyboardButton('🔙Назад', callback_data='back_to_main'))
    return markup

def get_country_action_keyboard(country):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton(f'✏️Переименовать страну', callback_data=f'rename_country_{country}'),
        InlineKeyboardButton(f'🗑️Удалить страну', callback_data=f'delete_country_{country}'),
        InlineKeyboardButton('🔙Назад', callback_data='back_to_countries')
    )
    return markup

def get_number_of_accounts_keyboard():
    markup = InlineKeyboardMarkup(row_width=3)
    for i in range(1, 10):
        markup.insert(InlineKeyboardButton(f"{i}", callback_data=f"number_{i}"))
    markup.add(
        InlineKeyboardButton('✏️Ввести свое значение', callback_data='custom_number'),
        InlineKeyboardButton('🔙Назад', callback_data='back_to_country_selection')
    )
    return markup

def get_format_management_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton('Добавить формат', callback_data='add_format'),
        InlineKeyboardButton('🔙Назад', callback_data='back_to_main')
    )
    return markup

def get_back_keyboard():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton('🔙Назад', callback_data='back_to_main'))
    return markup

def create_settings_buttons(settings):
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton(f"Эмодзи {'✅' if settings['emoji']['enabled'] else '❌'}", callback_data="toggle_emoji"),
        InlineKeyboardButton(f"Кол-во эмодзи: {settings['emoji']['count']}", callback_data="choose_emoji_count"),
        InlineKeyboardButton(f"Размер эмодзи: {settings['emoji']['size']}px", callback_data="choose_emoji_size"),
        InlineKeyboardButton(f"Непрозрачность эмодзи: {settings['emoji']['transparency']}%", callback_data="choose_emoji_transparency"),
        InlineKeyboardButton(f"Шумы {'✅' if settings['noise']['enabled'] else '❌'}", callback_data="toggle_noise"),
        InlineKeyboardButton(f"Интенсивность шума: {settings['noise']['intensity']}", callback_data="choose_noise_intensity"),
        InlineKeyboardButton(f"Фон {'✅' if settings['background']['enabled'] else '❌'}", callback_data="toggle_background"),
        InlineKeyboardButton(f"Непрозрачность фона: {settings['background']['transparency']}%", callback_data="choose_background_transparency"),
        InlineKeyboardButton(f"Кол-во уникализаций: {settings['unique_count']}", callback_data="choose_unique_count"),
        InlineKeyboardButton('🔙Назад', callback_data='back_to_main')
    )
    return markup

def create_unique_count_buttons():
    buttons = [
        [InlineKeyboardButton(text="1", callback_data="set_unique_count_1"),
         InlineKeyboardButton(text="2", callback_data="set_unique_count_2"),
         InlineKeyboardButton(text="3", callback_data="set_unique_count_3")],
        [InlineKeyboardButton(text="4", callback_data="set_unique_count_4"),
         InlineKeyboardButton(text="5", callback_data="set_unique_count_5")],
    ]
    buttons.append([InlineKeyboardButton("🔙Назад", callback_data="back_to_settings")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def create_emoji_count_buttons():
    buttons = [
        [InlineKeyboardButton("5", callback_data="set_emoji_count_5"),
         InlineKeyboardButton("10", callback_data="set_emoji_count_10"),
         InlineKeyboardButton("15", callback_data="set_emoji_count_15")],
        [InlineKeyboardButton("20", callback_data="set_emoji_count_20"),
         InlineKeyboardButton("30", callback_data="set_emoji_count_30")],
        [InlineKeyboardButton("Своё значение", callback_data="set_custom_emoji_count")],
        [InlineKeyboardButton("🔙Назад", callback_data="back_to_settings")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def create_emoji_size_buttons():
    buttons = [
        [InlineKeyboardButton("15", callback_data="set_emoji_size_15"),
         InlineKeyboardButton("25", callback_data="set_emoji_size_25"),
         InlineKeyboardButton("35", callback_data="set_emoji_size_35")],
        [InlineKeyboardButton("40", callback_data="set_emoji_size_40"),
         InlineKeyboardButton("Своё значение", callback_data="set_custom_emoji_size")],
        [InlineKeyboardButton("🔙Назад", callback_data="back_to_settings")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def create_emoji_transparency_buttons():
    buttons = [
        [InlineKeyboardButton("0%", callback_data="set_emoji_transparency_0"),
         InlineKeyboardButton("25%", callback_data="set_emoji_transparency_25"),
         InlineKeyboardButton("50%", callback_data="set_emoji_transparency_50")],
        [InlineKeyboardButton("75%", callback_data="set_emoji_transparency_75"),
         InlineKeyboardButton("100%", callback_data="set_emoji_transparency_100")],
        [InlineKeyboardButton("Своё значение", callback_data="set_custom_emoji_transparency")],
        [InlineKeyboardButton("🔙Назад", callback_data="back_to_settings")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def create_noise_intensity_buttons():
    buttons = [
        [InlineKeyboardButton("2.5", callback_data="set_noise_intensity_2.5"),
         InlineKeyboardButton("5", callback_data="set_noise_intensity_5"),
         InlineKeyboardButton("7.5", callback_data="set_noise_intensity_7.5")],
        [InlineKeyboardButton("10", callback_data="set_noise_intensity_10"),
         InlineKeyboardButton("12.5", callback_data="set_noise_intensity_12.5"),
         InlineKeyboardButton("15", callback_data="set_noise_intensity_15")],
        [InlineKeyboardButton("Своё значение", callback_data="set_custom_noise_intensity")],
        [InlineKeyboardButton("🔙Назад", callback_data="back_to_settings")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def create_background_transparency_buttons():
    buttons = [
        [InlineKeyboardButton("0%", callback_data="set_background_transparency_0"),
         InlineKeyboardButton("25%", callback_data="set_background_transparency_25"),
         InlineKeyboardButton("50%", callback_data="set_background_transparency_50")],
        [InlineKeyboardButton("75%", callback_data="set_background_transparency_75"),
         InlineKeyboardButton("100%", callback_data="set_background_transparency_100")],
        [InlineKeyboardButton("Своё значение", callback_data="set_custom_background_transparency")],
        [InlineKeyboardButton("🔙 Назад", callback_data="back_to_settings")]
    ]
    return InlineKeyboardMarkup(inline_keyboard=buttons)

def get_confirm_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton('✅Да', callback_data='confirm_yes'),
        InlineKeyboardButton('❌Нет', callback_data='confirm_no')
    )
    return markup

def get_retry_keyboard():
    markup = InlineKeyboardMarkup(row_width=1)
    markup.add(InlineKeyboardButton('🔁Попробовать снова', callback_data='get_code'))
    return markup

def get_admin_main_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton('Управление пользователями', callback_data='manage_users'),
        InlineKeyboardButton('Управление странами', callback_data='manage_countries'),
        InlineKeyboardButton('🔙Назад', callback_data='back_to_main')
    )
    return markup

def get_user_management_keyboard():
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(
        InlineKeyboardButton('Добавить пользователя', callback_data='add_user'),
        InlineKeyboardButton('Удалить пользователя', callback_data='delete_user'),
        InlineKeyboardButton('🔙Назад', callback_data='back_to_admin_main')
    )
    return markup

def get_user_details_keyboard(user_id):
    # Replace with actual implementation
    return "Детали пользователя (заглушка)"

def get_country_accounts_keyboard(country):
    # Replace with actual implementation
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton('🔙Назад', callback_data='back_to_admin_main'))
    return markup

def get_user_countries_keyboard(user_id):
    # Replace with actual implementation
    markup = InlineKeyboardMarkup(row_width=2)
    markup.add(InlineKeyboardButton('🔙Назад', callback_data='back_to_admin_main'))
    return markup


def get_admin_main_keyboard(total_users: int = None):
    keyboard = types.InlineKeyboardMarkup()
    
    if total_users is not None:
        keyboard.add(types.InlineKeyboardButton(f"Пользователей: {total_users}", callback_data="total_users"))
    else:
        keyboard.add(types.InlineKeyboardButton("Показать количество пользователей", callback_data="total_users"))

    keyboard.add(types.InlineKeyboardButton("Управление пользователями", callback_data="manage_users"))
    keyboard.add(types.InlineKeyboardButton("Добавить админа", callback_data="add_admin"))
    return keyboard

def get_users_page_keyboard(users, page, total_pages):
    kb = InlineKeyboardMarkup(row_width=1)
    for user_id, username, is_banned in users:
        label = f"{'❌' if is_banned else '✅'} {username or user_id}"
        kb.add(InlineKeyboardButton(label, callback_data=f"user_{user_id}"))
    nav = []
    if page > 0:
        nav.append(InlineKeyboardButton("⬅️", callback_data=f"page_{page - 1}"))
    if page < total_pages - 1:
        nav.append(InlineKeyboardButton("➡️", callback_data=f"page_{page + 1}"))
    if nav:
        kb.row(*nav)
    kb.add(InlineKeyboardButton("🔙Назад", callback_data="back_to_admin"))
    return kb

def get_user_manage_keyboard(user_id, is_banned):
    kb = InlineKeyboardMarkup(row_width=2)
    action = "unban" if is_banned else "ban"
    label = "✅ Разблокировать" if is_banned else "❌ Заблокировать"
    kb.add(
        InlineKeyboardButton(label, callback_data=f"{action}_{user_id}"),
        InlineKeyboardButton("📂Аккаунты", callback_data=f"accounts_{user_id}"),
        InlineKeyboardButton("⬅️Назад", callback_data="manage_users")
    )
    return kb

def get_all_users():
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, username, banned FROM users ORDER BY user_id")
    users = cursor.fetchall()
    conn.close()
    return users

def set_ban_status(user_id, banned: bool):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET banned = ? WHERE user_id = ?", (int(banned), user_id))
    conn.commit()
    conn.close()

def get_accounts_by_user(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("SELECT country, account FROM accounts WHERE user_id = ? ORDER BY country", (user_id,))
    accounts = cursor.fetchall()
    conn.close()
    return accounts

def add_admin(user_id):
    conn = sqlite3.connect(DB_NAME)
    cursor = conn.cursor()
    cursor.execute("INSERT OR IGNORE INTO admins (user_id) VALUES (?)", (user_id,))
    conn.commit()
    conn.close()
