import logging
import os
import asyncio
import random
import requests
from PIL import Image, ImageDraw
import numpy as np
from io import BytesIO
from aiogram import Bot, Dispatcher, executor, types
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters.state import State, StatesGroup
from aiogram.contrib.middlewares.logging import LoggingMiddleware
from config import API_TOKEN
import database as db
import get_code as gc
from keyboards import (
    get_main_keyboard, get_account_management_keyboard, get_my_accounts_keyboard,
    get_country_keyboard, get_country_management_keyboard, get_country_action_keyboard,
    get_back_keyboard, create_settings_buttons, create_unique_count_buttons,
    create_emoji_count_buttons, create_emoji_size_buttons, create_emoji_transparency_buttons,
    create_noise_intensity_buttons, create_background_transparency_buttons, 
    get_retry_keyboard, get_confirm_keyboard, get_format_management_keyboard,
    get_number_of_accounts_keyboard
)
from image_processing import process_image, compress_image
import re
from block_banned import BlockBannedMiddleware
from datetime import datetime, timedelta

user_last_unique_time = {}

# Constants
UNSPLASH_ACCESS_KEY = 'Bmnzc4D_qAtof9NADCncwaxGCPSOul26b1pwXUlH2fQ'
MAX_FILE_SIZE_MB = 5  # Максимальный размер файла в мегабайтах

# Logger setup
logging.basicConfig(level=logging.INFO)

# Bot and Dispatcher setup
bot = Bot(token=API_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(bot, storage=storage)
dp.middleware.setup(LoggingMiddleware())
dp.middleware.setup(BlockBannedMiddleware())

# Initialize DB
db.init_db()

# Default settings for image processing
settings = {
    'emoji': {'enabled': True, 'count': 1, 'size': 50, 'transparency': 50},
    'noise': {'enabled': True, 'intensity': 10},
    'background': {'enabled': True, 'transparency': 50},
    'unique_count': 1,
    'message_id': None
}

delayed_tasks = {}

# States for FSM
class Form(StatesGroup):
    action = State()
    country = State()
    new_country = State()
    number_of_accounts = State()
    file_upload = State()
    delete_country = State()
    custom_number = State()
    account_format = State()
    manage_formats = State()
    new_format = State()
    delete_format = State()
    get_code = State()
    confirm_delete_country = State()
    confirm_delete_format = State()
    confirm_rename_country = State()
    unique = State()
    custom_emoji_transparency = State()
    custom_background_transparency = State()
    custom_emoji_size = State()
    custom_emoji_count = State()
    custom_noise_intensity = State()


def compress_image(file_path):
    image = Image.open(file_path)
    compressed_path = f"processed_images/compressed_{os.path.basename(file_path)}"
    image.save(compressed_path, optimize=True, quality=85)
    logging.info(f"Compressed image saved as: {compressed_path}")
    logging.info(f"Compressed image size: {os.path.getsize(compressed_path) / 1024:.2f} KB")
    return compressed_path

# Helper functions for image processing
def clean_metadata(file_path):
    from exif import Image as ExifImage
    with open(file_path, 'rb') as img_file:
        img = ExifImage(img_file)
        if "APP1" in img._segments:
            try:
                img.delete_all()
            except Exception as e:
                logging.warning(f"Exception occurred while deleting EXIF data: {e}")
            with open(file_path, 'wb') as new_file:
                new_file.write(img.get_file())

def add_random_emoji(image, settings):
    emoji_files = [f for f in os.listdir('emoji') if os.path.isfile(os.path.join('emoji', f))]
    for _ in range(settings['emoji']['count']):
        emoji_file = random.choice(emoji_files)
        emoji = Image.open(os.path.join('emoji', emoji_file)).convert('RGBA')
        emoji = emoji.resize((settings['emoji']['size'], settings['emoji']['size']), Image.LANCZOS)
        x = random.randint(0, image.width - emoji.width)
        y = random.randint(0, image.height - emoji.height)
        emoji_mask = emoji.split()[3].point(lambda i: i * settings['emoji']['transparency'] / 100)
        image.paste(emoji, (x, y), emoji_mask)
    return image

def add_noise(image, settings):
    draw = ImageDraw.Draw(image)
    width, height = image.size
    factor = settings['noise']['intensity']
    for i in range(width):
        for j in range(height):
            rand = random.randint(-factor, factor)
            r, g, b, a = image.getpixel((i, j))
            r = max(0, min(255, r + rand))
            g = max(0, min(255, g + rand))
            b = max(0, min(255, b + rand))
            draw.point((i, j), (r, g, b, a))
    return image

def get_random_background():
    try:
        url = f'https://api.unsplash.com/photos/random?client_id={UNSPLASH_ACCESS_KEY}'
        response = requests.get(url)
        data = response.json()
        bg_url = data['urls']['full']
        bg_image = Image.open(requests.get(bg_url, stream=True).raw).convert('RGBA')
        logging.info(f"Background image loaded from {bg_url}")
        return bg_image
    except Exception as e:
        logging.error(f"Error loading background image: {e}")
        return None

def add_background(image, settings):
    bg_image = get_random_background()
    if bg_image is not None:
        bg_image = bg_image.resize(image.size)
        bg_image = Image.blend(image, bg_image, settings['background']['transparency'] / 100)
        logging.info("Background image added")
    else:
        logging.warning("No background image added")
    return bg_image

def process_image(file_path, settings):
    clean_metadata(file_path)
    image = Image.open(file_path).convert('RGBA')
    logging.info(f"Original image size: {os.path.getsize(file_path) / 1024:.2f} KB")
    
    if settings['emoji']['enabled']:
        image = add_random_emoji(image, settings)
    if settings['noise']['enabled']:
        image = add_noise(image, settings)
    if settings['background']['enabled']:
        image = add_background(image, settings)
    
    # Проверка существования каталога для сохранения
    if not os.path.exists("processed_images"):
        os.makedirs("processed_images")
    
    output_path = f"processed_images/unique_{random.randint(1000, 9999)}.jpg"
    image.convert('RGB').save(output_path, "JPEG", quality=85)
    logging.info(f"Processed image saved as: {output_path}")
    logging.info(f"Processed image size: {os.path.getsize(output_path) / 1024:.2f} KB")
    return output_path

@dp.callback_query_handler(lambda call: call.data.startswith("set_") or call.data.startswith("choose_") or call.data == "back_to_settings", state=Form.unique)
async def handle_unique_settings(call: types.CallbackQuery, state: FSMContext):
    await call.answer()
    data = call.data

    # Установка значений
    if data.startswith("set_unique_count_"):
        settings['unique_count'] = int(data.split("_")[-1])
        await call.answer("✅ Количество уникализаций обновлено")
    elif data.startswith("set_emoji_count_"):
        settings['emoji']['count'] = int(data.split("_")[-1])
        await call.answer(f"✅ Кол-во эмодзи: {settings['emoji']['count']}")
    elif data.startswith("set_emoji_size_"):
        settings['emoji']['size'] = int(data.split("_")[-1])
        await call.answer(f"✅ Размер эмодзи: {settings['emoji']['size']}")
    elif data.startswith("set_emoji_transparency_"):
        settings['emoji']['transparency'] = int(data.split("_")[-1])
        await call.answer(f"✅ Прозрачность эмодзи: {settings['emoji']['transparency']}%")
    elif data.startswith("set_noise_intensity_"):
        settings['noise']['intensity'] = float(data.split("_")[-1])
        await call.answer(f"✅ Интенсивность шума: {settings['noise']['intensity']}")
    elif data.startswith("set_background_transparency_"):
        settings['background']['transparency'] = int(data.split("_")[-1])
        await call.answer(f"✅ Прозрачность фона: {settings['background']['transparency']}%")

    # Кастомные значения
    elif data == "set_custom_emoji_size":
        await Form.custom_emoji_size.set()
        await bot.edit_message_text("Введите размер эмодзи (например 25):", call.message.chat.id, call.message.message_id)
        return
    elif data == "set_custom_emoji_count":
        await Form.custom_emoji_count.set()
        await bot.edit_message_text("Введите количество эмодзи (например 10):", call.message.chat.id, call.message.message_id)
        return
    elif data == "set_custom_noise_intensity":
        await Form.custom_noise_intensity.set()
        await bot.edit_message_text("Введите интенсивность шума (например 5.0):", call.message.chat.id, call.message.message_id)
        return
    elif data == "set_custom_emoji_transparency":
        await Form.custom_emoji_transparency.set()
        await bot.edit_message_text("Введите прозрачность эмодзи (от 0 до 100):", call.message.chat.id, call.message.message_id)
        return
    elif data == "set_custom_background_transparency":
        await Form.custom_background_transparency.set()
        await bot.edit_message_text("Введите прозрачность фона (от 0 до 100):", call.message.chat.id, call.message.message_id)
        return

    # Возврат к настройкам
    elif data == "back_to_settings":
        await bot.edit_message_text("Настройки уникализации:", call.message.chat.id, call.message.message_id, reply_markup=create_settings_buttons(settings))
        return

    # Выбор категорий
    elif data == "choose_unique_count":
        await bot.edit_message_text("Выберите количество уникализаций:", call.message.chat.id, call.message.message_id, reply_markup=create_unique_count_buttons())
        return
    elif data == "choose_emoji_count":
        await bot.edit_message_text("Выберите количество эмодзи:", call.message.chat.id, call.message.message_id, reply_markup=create_emoji_count_buttons())
        return
    elif data == "choose_emoji_size":
        await bot.edit_message_text("Выберите размер эмодзи:", call.message.chat.id, call.message.message_id, reply_markup=create_emoji_size_buttons())
        return
    elif data == "choose_emoji_transparency":
        await bot.edit_message_text("Выберите непрозрачность эмодзи:", call.message.chat.id, call.message.message_id, reply_markup=create_emoji_transparency_buttons())
        return
    elif data == "choose_noise_intensity":
        await bot.edit_message_text("Выберите интенсивность шума:", call.message.chat.id, call.message.message_id, reply_markup=create_noise_intensity_buttons())
        return
    elif data == "choose_background_transparency":
        await bot.edit_message_text("Выберите прозрачность фона:", call.message.chat.id, call.message.message_id, reply_markup=create_background_transparency_buttons())
        return

    # Обновляем главное меню, если был установлен параметр
    if settings.get('message_id'):
        await update_message(call.message.chat.id, settings['message_id'])

@dp.message_handler(lambda m: m.text.isdigit(), state=Form.custom_emoji_size)
async def handle_custom_emoji_size(message: types.Message, state: FSMContext):
    settings['emoji']['size'] = int(message.text)
    await state.finish()
    await Form.unique.set()

    if settings.get('message_id'):
        try:
            await bot.delete_message(message.chat.id, settings['message_id'])
        except Exception as e:
            logging.warning(f"Не удалось удалить старое сообщение: {e}")

    msg = await message.answer(
        f"✅ Размер эмодзи установлен на {message.text}",
        reply_markup=create_settings_buttons(settings)
    )
    settings['message_id'] = msg.message_id

@dp.message_handler(lambda m: m.text.isdigit(), state=Form.custom_emoji_count)
async def handle_custom_emoji_count(message: types.Message, state: FSMContext):
    settings['emoji']['count'] = int(message.text)
    await state.finish()
    await Form.unique.set()

    if settings.get('message_id'):
        try:
            await bot.delete_message(message.chat.id, settings['message_id'])
        except Exception as e:
            logging.warning(f"Не удалось удалить старое сообщение: {e}")

    msg = await message.answer(
        f"✅ Кол-во эмодзи установлено на {message.text}",
        reply_markup=create_settings_buttons(settings)
    )
    settings['message_id'] = msg.message_id

@dp.message_handler(lambda m: re.match(r'^(\d+(\.\d+)?)$', m.text), state=Form.custom_noise_intensity)
async def handle_custom_noise_intensity(message: types.Message, state: FSMContext):
    settings['noise']['intensity'] = float(message.text)
    await state.finish()
    await Form.unique.set()

    if settings.get('message_id'):
        try:
            await bot.delete_message(message.chat.id, settings['message_id'])
        except Exception as e:
            logging.warning(f"Не удалось удалить старое сообщение: {e}")

    msg = await message.answer(
        f"✅ Интенсивность шума установлена на {message.text}",
        reply_markup=create_settings_buttons(settings)
    )
    settings['message_id'] = msg.message_id

@dp.callback_query_handler(lambda call: call.data == "set_custom_emoji_size", state=Form.unique)
async def ask_custom_emoji_size(call: types.CallbackQuery, state: FSMContext):
    await Form.custom_emoji_size.set()
    await bot.edit_message_text("Введите размер эмодзи (например 25):", call.from_user.id, call.message.message_id)

@dp.callback_query_handler(lambda call: call.data == "set_custom_emoji_count", state=Form.unique)
async def ask_custom_emoji_count(call: types.CallbackQuery, state: FSMContext):
    await Form.custom_emoji_count.set()
    await bot.edit_message_text("Введите количество эмодзи (например 10):", call.from_user.id, call.message.message_id)

@dp.callback_query_handler(lambda call: call.data == "set_custom_noise_intensity", state=Form.unique)
async def ask_custom_noise_intensity(call: types.CallbackQuery, state: FSMContext):
    await Form.custom_noise_intensity.set()
    await bot.edit_message_text("Введите интенсивность шума (например 5.0):", call.from_user.id, call.message.message_id)

@dp.callback_query_handler(lambda c: c.data == 'back_to_country_selection', state='*')
async def back_to_country_selection(callback_query: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    user_id = callback_query.from_user.id
    action = user_data.get('action')
    
    if action == 'add_accounts':
        await Form.country.set()
        await bot.edit_message_text("Выберите страну:", user_id, callback_query.message.message_id, reply_markup=get_country_keyboard(user_id))
    elif action == 'get_accounts':
        await Form.country.set()
        await bot.edit_message_text("Выберите страну:", user_id, callback_query.message.message_id, reply_markup=get_country_keyboard(user_id))


@dp.message_handler(lambda m: m.text.isdigit(), state=Form.custom_emoji_transparency)
async def set_custom_emoji_transparency(message: types.Message, state: FSMContext):
    value = int(message.text)
    if 0 <= value <= 100:
        settings['emoji']['transparency'] = value
        await state.finish()
        await Form.unique.set()

        if settings.get('message_id'):
            try:
                await bot.delete_message(message.chat.id, settings['message_id'])
            except Exception as e:
                logging.warning(f"Не удалось удалить старое сообщение: {e}")

        msg = await message.answer(
            f"✅ Прозрачность эмодзи установлена на {value}%",
            reply_markup=create_settings_buttons(settings)
        )
        settings['message_id'] = msg.message_id
    else:
        await message.answer("Введите число от 0 до 100.")

@dp.message_handler(lambda m: m.text.isdigit(), state=Form.custom_background_transparency)
async def set_custom_background_transparency(message: types.Message, state: FSMContext):
    value = int(message.text)
    if 0 <= value <= 100:
        settings['background']['transparency'] = value
        await state.finish()
        await Form.unique.set()

        if settings.get('message_id'):
            try:
                await bot.delete_message(message.chat.id, settings['message_id'])
            except Exception as e:
                logging.warning(f"Не удалось удалить старое сообщение: {e}")

        msg = await message.answer(
            f"✅ Прозрачность фона установлена на {value}%",
            reply_markup=create_settings_buttons(settings)
        )
        settings['message_id'] = msg.message_id
    else:
        await message.answer("Введите число от 0 до 100.")

@dp.message_handler(lambda message: message.text.isdigit(), state=Form.custom_emoji_transparency)
async def set_custom_emoji_transparency(message: types.Message, state: FSMContext):
    value = int(message.text)
    if 0 <= value <= 100:
        settings['emoji']['transparency'] = value
        await message.answer(
            f"✅ Прозрачность эмодзи установлена на {value}%",
            reply_markup=create_settings_buttons(settings)
        )
        await state.finish()  # ← этого достаточно
    else:
        await message.answer("Введите число от 0 до 100.")

@dp.message_handler(lambda message: message.text.isdigit(), state=Form.custom_background_transparency)
async def set_custom_background_transparency(message: types.Message, state: FSMContext):
    value = int(message.text)
    if 0 <= value <= 100:
        settings['background']['transparency'] = value
        await message.answer(
            f"✅ Прозрачность фона установлена на {value}%",
            reply_markup=create_settings_buttons(settings)
        )
        await state.finish()  # ← этого достаточно
    else:
        await message.answer("Введите число от 0 до 100.")

# Handlers
@dp.message_handler(commands=['start'])
async def send_welcome(message: types.Message):
    user = db.get_user_by_id(message.from_user.id)
    if user and user[3] == 1:  # если забанен
        return await message.reply("⛔ Вы заблокированы.")
    db.add_user(message.from_user.id, message.from_user.username)
    await Form.action.set()
    await message.reply("Привет! Я TT Helper для управления аккаунтами и уникализации фото/видео. Выберите действие:", reply_markup=get_main_keyboard())

async def handle_media(state: FSMContext, chat_id: int):
    try:
        user_data = await state.get_data()
        media_files = user_data.get('media_files', [])

        if not media_files:
            return  # Ничего не делать, если файлов нет

        processed_files = []

        # Обрабатываем все фото/документы из списка
        for message in media_files:
            if message.photo:
                file_id = message.photo[-1].file_id
            elif message.document:
                file_id = message.document.file_id
            else:
                continue
            
            file = await bot.get_file(file_id)
            downloaded_file = await bot.download_file(file.file_path)
            
            with open("temp_image.png", "wb") as new_file:
                new_file.write(downloaded_file.getvalue())
            
            for i in range(settings['unique_count']):
                processed_file = process_image("temp_image.png", settings)

                file_size = os.path.getsize(processed_file) / (1024 * 1024)
                if file_size > 3.5:
                    compressed_file = compress_image(processed_file)
                else:
                    compressed_file = processed_file

                processed_files.append(compressed_file)

                if compressed_file != processed_file and os.path.exists(processed_file):
                    os.remove(processed_file)

            if os.path.exists("temp_image.png"):
                os.remove("temp_image.png")

            if processed_file != compressed_file and os.path.exists(processed_file):
                os.remove(processed_file)

        # Отправляем ВСЕ файлы разом
        for file in processed_files:
            with open(file, "rb") as img:
                await bot.send_document(chat_id, img, caption="Ваше уникализированное изображение готово!")
            if os.path.exists(file):
                os.remove(file)

        # Отправка нового меню ПОСЛЕ ВСЕХ ФАЙЛОВ
        markup = create_settings_buttons(settings)
        sent_message = await bot.send_message(chat_id, "Настройки обновлены:", reply_markup=markup)
        settings['message_id'] = sent_message.message_id

        # Очищаем список медиафайлов
        await state.update_data(media_files=[])

    except Exception as e:
        logging.error(f"Ошибка при обработке изображения: {e}")

@dp.callback_query_handler(lambda c: c.data in ['manage_accounts', 'my_accounts', 'get_code', 'manage_countries', 'unique'], state=Form.action)
async def process_action(callback_query: types.CallbackQuery, state: FSMContext):
    action = callback_query.data
    user_id = callback_query.from_user.id

    if action == 'unique':
        # Удаляем сообщение главного меню
        try:
            await bot.delete_message(callback_query.message.chat.id, callback_query.message.message_id)
        except Exception as e:
            logging.warning(f"❗ Не удалось удалить главное меню: {e}")

        # Удаляем старое меню уникализации, если оно было
        if settings['message_id']:
            try:
                await bot.delete_message(callback_query.from_user.id, settings['message_id'])
                settings['message_id'] = None
            except Exception as e:
                logging.warning(f"⚠️ Не удалось удалить предыдущее меню уникализации: {e}")

        await Form.unique.set()  # Устанавливаем состояние уникализации

        markup = create_settings_buttons(settings)
        sent_message = await bot.send_message(
            callback_query.from_user.id,
            "Добро пожаловать в уникализатор! Настройте свои параметры:",
            reply_markup=markup
        )
        settings['message_id'] = sent_message.message_id  # Сохраняем ID нового сообщения

    elif action == 'manage_accounts':
        await bot.edit_message_text("Выберите действие:", user_id, callback_query.message.message_id, reply_markup=get_account_management_keyboard())

    elif action == 'my_accounts':
        response = get_my_accounts_keyboard(user_id)
        await bot.edit_message_text(response, user_id, callback_query.message.message_id, reply_markup=get_back_keyboard())

    elif action == 'get_code':
        await Form.get_code.set()
        await bot.edit_message_text(
            "Отправьте аккаунт в любом формате, например mail|mailpass|login|pass|refreshtoken|clientid:",
            user_id,
            callback_query.message.message_id,
            reply_markup=get_back_keyboard()
        )

    elif action == 'manage_countries':
        await bot.edit_message_text("Управление странами:", user_id, callback_query.message.message_id, reply_markup=get_country_management_keyboard(user_id))

@dp.message_handler(content_types=['photo', 'document'], state=Form.unique)
async def handle_media_wrapper(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    now = datetime.now()
    last_time = user_last_unique_time.get(user_id)

    # Ограничение по времени
    if last_time and now - last_time < timedelta(minutes=3):
        await message.answer("⏳ Уникализация доступна раз в 3 минуты. Пожалуйста, подождите.")
        return

    user_data = await state.get_data()
    media_files = user_data.get('media_files', [])
    
    # Проверка лимита файлов
    if len(media_files) >= 5:
        await message.answer("⚠️ Можно уникализировать не более 5 файлов за один раз.")
        return

    media_files.append(message)
    await state.update_data(media_files=media_files)

    # Если уже 5 файлов — запускаем обработку
    if len(media_files) == 5:
        user_last_unique_time[user_id] = now
        await handle_media(state, message.chat.id)

@dp.callback_query_handler(lambda c: c.data == 'toggle_emoji', state='*')
async def toggle_emoji(call: types.CallbackQuery):
    await call.answer()
    settings['emoji']['enabled'] = not settings['emoji']['enabled']
    if settings.get('message_id'):
        await update_message(call.message.chat.id, settings['message_id'])

@dp.callback_query_handler(lambda c: c.data == 'toggle_noise', state='*')
async def toggle_noise(call: types.CallbackQuery):
    await call.answer()
    settings['noise']['enabled'] = not settings['noise']['enabled']
    if settings.get('message_id'):
        await update_message(call.message.chat.id, settings['message_id'])

@dp.callback_query_handler(lambda c: c.data == 'toggle_background', state='*')
async def toggle_background(call: types.CallbackQuery):
    await call.answer()
    settings['background']['enabled'] = not settings['background']['enabled']
    if settings.get('message_id'):
        await update_message(call.message.chat.id, settings['message_id'])

@dp.callback_query_handler(lambda c: c.data == 'choose_emoji_count', state=Form.unique)
async def choose_emoji_count(call: types.CallbackQuery):
    await bot.edit_message_text("Выберите количество эмодзи:", call.message.chat.id, call.message.message_id, reply_markup=create_emoji_count_buttons())

@dp.callback_query_handler(lambda c: c.data == 'choose_emoji_size', state=Form.unique)
async def choose_emoji_size(call: types.CallbackQuery):
    await bot.edit_message_text("Выберите размер эмодзи:", call.message.chat.id, call.message.message_id, reply_markup=create_emoji_size_buttons())

@dp.callback_query_handler(lambda c: c.data == 'choose_emoji_transparency', state=Form.unique)
async def choose_emoji_transparency(call: types.CallbackQuery):
    await bot.edit_message_text("Выберите прозрачность эмодзи:", call.message.chat.id, call.message.message_id, reply_markup=create_emoji_transparency_buttons())

@dp.callback_query_handler(lambda c: c.data == 'choose_noise_intensity', state=Form.unique)
async def choose_noise_intensity(call: types.CallbackQuery):
    await bot.edit_message_text("Выберите интенсивность шума:", call.message.chat.id, call.message.message_id, reply_markup=create_noise_intensity_buttons())

@dp.callback_query_handler(lambda c: c.data == 'choose_background_transparency', state=Form.unique)
async def choose_background_transparency(call: types.CallbackQuery):
    await bot.edit_message_text("Выберите непрозрачность фона:", call.message.chat.id, call.message.message_id, reply_markup=create_background_transparency_buttons())

# Остальные обработчики...

@dp.message_handler(state=Form.get_code)
async def handle_get_code(message: types.Message, state: FSMContext):
    email_address, mailpass, refreshtoken, clientid = gc.extract_tokens(message.text)
    if email_address and refreshtoken and clientid:
        await state.update_data(email_address=email_address, refreshtoken=refreshtoken, clientid=clientid)
        access_token = gc.get_access_token(refreshtoken, clientid)
        if access_token:
            code = gc.get_code_from_email_hotmail(email_address, access_token)
            if code:
                await message.reply(f"Ваш код TikTok: {code}")
            else:
                await message.reply("Код не найден. Попробуйте еще раз.", reply_markup=get_retry_keyboard())
        else:
            await message.reply("Ошибка при получении токена доступа.", reply_markup=get_retry_keyboard())
    else:
        await message.reply("Некорректный формат. Пожалуйста, отправьте аккаунт в любом формате, например mail|mailpass|login|pass|refreshtoken|clientid.")
    await state.finish()
    await send_welcome(message)

@dp.callback_query_handler(lambda c: c.data in ['add_accounts', 'get_accounts', 'back_to_main'], state=Form.action)
async def handle_account_management(callback_query: types.CallbackQuery, state: FSMContext):
    action = callback_query.data
    user_id = callback_query.from_user.id
    if action == 'add_accounts':
        await state.update_data(action='add_accounts')
        await Form.country.set()
        await bot.edit_message_text("Выберите страну:", callback_query.from_user.id, callback_query.message.message_id, reply_markup=get_country_keyboard(user_id))
    elif action == 'get_accounts':
        await state.update_data(action='get_accounts')
        await Form.country.set()
        await bot.edit_message_text("Выберите страну:", callback_query.from_user.id, callback_query.message.message_id, reply_markup=get_country_keyboard(user_id))
    elif action == 'back_to_main':
        await state.finish()
        await Form.action.set()
        await bot.edit_message_text("Привет! Я бот для управления аккаунтами/уникализации. Выберите действие:", callback_query.from_user.id, callback_query.message.message_id, reply_markup=get_main_keyboard())

@dp.callback_query_handler(lambda c: c.data.startswith('manage_country_'), state=Form.action)
async def handle_manage_country(callback_query: types.CallbackQuery, state: FSMContext):
    country = callback_query.data.split('_')[2]
    user_id = callback_query.from_user.id
    await state.update_data(country=country)
    await Form.country.set()
    await bot.edit_message_text(f"Выберите действие для страны '{country}':", callback_query.from_user.id, callback_query.message.message_id, reply_markup=get_country_action_keyboard(country))

@dp.callback_query_handler(lambda c: c.data.startswith('country_'), state=Form.country)
async def handle_country(callback_query: types.CallbackQuery, state: FSMContext):
    country = callback_query.data.split('_')[1]
    user_data = await state.get_data()
    action = user_data.get('action')
    user_id = callback_query.from_user.id
    if action == 'add_accounts':
        await state.update_data(country=country)
        await bot.edit_message_text(
    "Загрузите файл с аккаунтами в формате .txt или отправьте текстовое сообщение с аккаунтами:",
    callback_query.from_user.id,
    callback_query.message.message_id,
    reply_markup=get_back_keyboard()
)
        await Form.file_upload.set()
    elif action == 'get_accounts':
        await state.update_data(country=country)
        await bot.edit_message_text(
    "Укажите количество аккаунтов, которые вы хотите получить:",
    callback_query.from_user.id,
    callback_query.message.message_id,
    reply_markup=get_number_of_accounts_keyboard()
)
        await Form.number_of_accounts.set()
    elif action == 'manage_countries':
        await state.update_data(country=country)
        await bot.edit_message_text(f"Выберите действие для страны '{country}':", callback_query.from_user.id, callback_query.message.message_id, reply_markup=get_country_action_keyboard(country))

@dp.callback_query_handler(lambda c: c.data.startswith('delete_country_'), state=Form.country)
async def handle_delete_country(callback_query: types.CallbackQuery, state: FSMContext):
    country_to_delete = callback_query.data.split('_')[2]
    await state.update_data(country=country_to_delete)
    await Form.confirm_delete_country.set()
    await bot.edit_message_text(f"Вы уверены, что хотите удалить страну '{country_to_delete}'? Да/Нет", callback_query.from_user.id, callback_query.message.message_id, reply_markup=get_confirm_keyboard())

@dp.callback_query_handler(lambda c: c.data == 'confirm_yes', state=Form.confirm_delete_country)
async def confirm_delete_country_yes(callback_query: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    country_to_delete = user_data.get('country')
    user_id = callback_query.from_user.id
    db.delete_country(user_id, country_to_delete)
    await bot.edit_message_text(f"Страна '{country_to_delete}' успешно удалена.", callback_query.from_user.id, callback_query.message.message_id, reply_markup=get_main_keyboard())
    await Form.action.set()

@dp.callback_query_handler(lambda c: c.data == 'confirm_no', state=Form.confirm_delete_country)
async def confirm_delete_country_no(callback_query: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    country = user_data.get('country')
    await bot.edit_message_text(f"Выберите действие для страны '{country}':", callback_query.from_user.id, callback_query.message.message_id, reply_markup=get_country_action_keyboard(country))
    await Form.country.set()

@dp.callback_query_handler(lambda c: c.data.startswith('rename_country_'), state=Form.country)
async def confirm_rename_country(callback_query: types.CallbackQuery, state: FSMContext):
    country = callback_query.data.split('_')[2]
    await state.update_data(country=country)
    await Form.new_country.set()
    await bot.edit_message_text(f"Введите новое название для страны '{country}':", callback_query.from_user.id, callback_query.message.message_id, reply_markup=get_back_keyboard())

@dp.callback_query_handler(lambda c: c.data == 'new_country', state=Form.action)
async def new_country(callback_query: types.CallbackQuery, state: FSMContext):
    await Form.new_country.set()
    await bot.edit_message_text("Введите название новой страны:", callback_query.from_user.id, callback_query.message.message_id, reply_markup=get_back_keyboard())

@dp.message_handler(state=Form.new_country)
async def handle_new_country(message: types.Message, state: FSMContext):
    new_country = message.text
    user_id = message.from_user.id
    user_data = await state.get_data()
    if 'country' in user_data:
        old_country = user_data.get('country')
        db.rename_country(user_id, old_country, new_country)
        await message.reply(f"Страна '{old_country}' переименована в '{new_country}'.", reply_markup=get_main_keyboard())
    else:
        db.add_country(user_id, new_country)
        await message.reply(f"Страна '{new_country}' добавлена.", reply_markup=get_main_keyboard())
    await state.finish()
    await Form.action.set()

@dp.message_handler(state=Form.file_upload, content_types=types.ContentTypes.TEXT)
async def handle_file_upload(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    country = user_data.get('country')
    user_id = message.from_user.id
    accounts = message.text.split('\n')
    for account in accounts:
        db.add_account(user_id, country, account, 'default_format')
    await message.reply(f"Аккаунты для страны '{country}' успешно добавлены.", reply_markup=get_main_keyboard())
    await Form.action.set()

@dp.message_handler(state=Form.file_upload, content_types=types.ContentTypes.DOCUMENT)
async def handle_file_upload_document(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    country = user_data.get('country')
    user_id = message.from_user.id
    document = message.document
    file = await message.bot.download_file_by_id(document.file_id)
    accounts = file.read().decode('utf-8').split('\n')
    for account in accounts:
        db.add_account(user_id, country, account, 'default_format')
    await message.reply(f"Аккаунты для страны '{country}' успешно добавлены.", reply_markup=get_main_keyboard())
    await Form.action.set()

@dp.callback_query_handler(lambda c: c.data.startswith('number_'), state=Form.number_of_accounts)
async def handle_number_callback(callback_query: types.CallbackQuery, state: FSMContext):
    number = int(callback_query.data.split('_')[1])
    user_data = await state.get_data()
    country = user_data.get('country')
    user_id = callback_query.from_user.id

    # ❗ Удаляем сообщение с кнопками
    try:
        await bot.delete_message(user_id, callback_query.message.message_id)
    except Exception as e:
        logging.warning(f"Не удалось удалить сообщение с кнопками: {e}")

    accounts = db.get_accounts(user_id, country, number)
    response = '\n'.join(accounts) or "Нет доступных аккаунтов."

    if accounts:
        for account in accounts:
            db.delete_account(user_id, country, account)

    if len(accounts) > 5:
        filename = f"accounts_{user_id}.txt"
        with open(filename, "w", encoding="utf-8") as f:
            f.write('\n'.join(accounts))
        await bot.send_document(user_id, types.InputFile(filename))
        os.remove(filename)
    else:
        await bot.send_message(user_id, response)
    await bot.send_message(user_id, "Что хотите сделать дальше?", reply_markup=get_main_keyboard())  # 2. Меню отдельно
    await state.finish()
    await send_welcome(callback_query.message)

@dp.callback_query_handler(lambda c: c.data == 'custom_number', state=Form.number_of_accounts)
async def handle_custom_number(callback_query: types.CallbackQuery, state: FSMContext):
    await Form.custom_number.set()
    await bot.edit_message_text("Введите количество аккаунтов:", callback_query.from_user.id, callback_query.message.message_id, reply_markup=get_back_keyboard())

@dp.message_handler(state=Form.custom_number)
async def handle_custom_number_input(message: types.Message, state: FSMContext):
    try:
        number_of_accounts = int(message.text)
        user_data = await state.get_data()
        country = user_data.get('country')
        user_id = message.from_user.id
        accounts = db.get_accounts(user_id, country, number_of_accounts)
        response = '\n'.join(accounts) or "Нет доступных аккаунтов."
        if accounts:
            for account in accounts:
                db.delete_account(user_id, country, account)
        if len(accounts) > 5:
            filename = f"accounts_{user_id}.txt"
            with open(filename, "w", encoding="utf-8") as f:
                f.write('\n'.join(accounts))
            await message.answer_document(types.InputFile(filename))
            os.remove(filename)
        else:
            await message.reply(response)

        await message.answer("Что хотите сделать дальше?", reply_markup=get_main_keyboard())
        await state.finish()
        await send_welcome(message)
    except ValueError:
        await message.reply("Пожалуйста, введите корректное число.", reply_markup=get_back_keyboard())
    try:
        await bot.delete_message(message.chat.id, message.message_id)
    except Exception as e:
        logging.warning(f"Не удалось удалить сообщение с кнопками: {e}")

@dp.callback_query_handler(lambda c: c.data.startswith('delete_format_'), state=Form.manage_formats)
async def handle_delete_format(callback_query: types.CallbackQuery, state: FSMContext):
    format_to_delete = callback_query.data.split('_')[2]
    await state.update_data(format=format_to_delete)
    await Form.confirm_delete_format.set()
    await bot.edit_message_text(f"Вы уверены, что хотите удалить формат '{format_to_delete}'? Да/Нет", callback_query.from_user.id, callback_query.message.message_id, reply_markup=get_confirm_keyboard())

@dp.callback_query_handler(lambda c: c.data == 'confirm_yes', state=Form.confirm_delete_format)
async def confirm_delete_format_yes(callback_query: types.CallbackQuery, state: FSMContext):
    user_data = await state.get_data()
    format_to_delete = user_data.get('format')
    db.delete_format(format_to_delete)
    await bot.edit_message_text(f"Формат '{format_to_delete}' успешно удален.", callback_query.from_user.id, callback_query.message.message_id, reply_markup=get_format_management_keyboard())
    await Form.manage_formats.set()

@dp.callback_query_handler(lambda c: c.data == 'confirm_no', state=Form.confirm_delete_format)
async def confirm_delete_format_no(callback_query: types.CallbackQuery, state: FSMContext):
    await Form.manage_formats.set()
    await bot.edit_message_text("Управление форматами:", callback_query.from_user.id, callback_query.message.message_id, reply_markup=get_format_management_keyboard())

@dp.callback_query_handler(lambda c: c.data == 'add_format', state=Form.manage_formats)
async def add_format(callback_query: types.CallbackQuery, state: FSMContext):
    await Form.new_format.set()
    await bot.edit_message_text("Введите новый формат (например, email|emailpass|login|pass|reftoken|clientid):", callback_query.from_user.id, callback_query.message.message_id, reply_markup=get_back_keyboard())

@dp.message_handler(state=Form.new_format)
async def handle_new_format(message: types.Message, state: FSMContext):
    new_format = message.text
    required_fields = ["email", "emailpass", "login", "pass", "reftoken", "clientid"]
    if all(field in new_format for field in required_fields):
        db.add_format(new_format)
        await message.reply(f"Формат '{new_format}' успешно добавлен.", reply_markup=get_format_management_keyboard())
        await Form.manage_formats.set()
    else:
        await message.reply(f"Формат '{new_format}' не содержит все необходимые поля (email, emailpass, login, pass, reftoken, clientid).", reply_markup=get_back_keyboard())
        await Form.manage_formats.set()

@dp.callback_query_handler(lambda c: c.data == 'back_to_main', state='*')
async def back_to_main(callback_query: types.CallbackQuery, state: FSMContext):
    await state.finish()
    await Form.action.set()
    await bot.edit_message_text("Привет! Я бот для управления аккаунтами. Выберите действие:", callback_query.from_user.id, callback_query.message.message_id, reply_markup=get_main_keyboard())

@dp.callback_query_handler(lambda c: c.data == 'back_to_countries', state=Form.country)
async def back_to_countries(callback_query: types.CallbackQuery, state: FSMContext):
    user_id = callback_query.from_user.id
    await bot.edit_message_text("Управление странами:", user_id, callback_query.message.message_id, reply_markup=get_country_management_keyboard(user_id))
    await Form.country.set()

async def update_message(chat_id, old_message_id):
    try:
        # Пытаемся удалить старое сообщение
        await bot.delete_message(chat_id, old_message_id)
    except Exception as e:
        logging.warning(f"⚠️ Не удалось удалить старое сообщение: {e}")

    try:
        # Отправляем новое меню с актуальными настройками
        new_msg = await bot.send_message(chat_id, "Настройки обновлены:", reply_markup=create_settings_buttons(settings))
        settings['message_id'] = new_msg.message_id
    except Exception as e:
        logging.error(f"❌ Ошибка при отправке нового меню: {e}")

if __name__ == '__main__':
    import asyncio
    loop = asyncio.get_event_loop()
    loop.create_task(dp.start_polling())
    loop.run_forever()