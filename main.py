from aiogram.types import FSInputFile
import html
import logging
import json
from gtts import gTTS
import os
import asyncio
from datetime import datetime
import random

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram import F
from deep_translator import GoogleTranslator
from langdetect import detect

info_logger = logging.getLogger("bot_info")
info_logger.setLevel(logging.INFO)
info_handler = logging.FileHandler("bot.log", encoding="utf-8")
info_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
info_handler.setFormatter(info_formatter)
info_logger.addHandler(info_handler)

error_logger = logging.getLogger("bot_errors")
error_logger.setLevel(logging.ERROR)
error_handler = logging.FileHandler("errors.log", encoding="utf-8")
error_formatter = logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
error_handler.setFormatter(error_formatter)
error_logger.addHandler(error_handler)

BOT_TOKEN = os.getenv("BOT_TOKEN", "8285221368:AAGeHopGEPs22eZfXbA-U_-Fdn9tqpeuDwM")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан. Установите переменную окружения BOT_TOKEN.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

STATS_FILE = "stats.json"
if os.path.exists(STATS_FILE):
    with open(STATS_FILE, "r", encoding="utf-8") as f:
        stats = json.load(f)
else:
    stats = {}

def update_stats(user_id: int, command: str):
    user_id = str(user_id)
    if user_id not in stats:
        stats[user_id] = {"messages": 0, "commands": {}}
    stats[user_id]["messages"] += 1
    stats[user_id]["commands"][command] = stats[user_id]["commands"].get(command, 0) + 1

    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=4)

users = set()
first_start_times = {}
user_names = {}
user_langs = {}

@dp.message(Command(commands=["start"]))
async def send_hello(message: types.Message):
    try:
        update_stats(message.from_user.id, "/start")

        user_id = message.from_user.id
        user_name = message.from_user.first_name or "Пользователь"
        info_logger.info(f"Пользователь {user_name} (ID: {user_id}) вызвал /start")

        if user_id not in first_start_times:
            first_start_times[user_id] = datetime.now().strftime("%d.%m.%Y %H:%M")

        banner = (
            "💫 <b>Добро пожаловать в Бота-Переводчика!</b>\n\n"
            "🌍 Я создан, чтобы помогать тебе мгновенно переводить тексты на десятки языков мира.\n"
            "🎧 А ещё я умею <b>озвучивать</b> переводы и показывать твою статистику.\n\n"
            "📘 <b>Что я умею:</b>\n"
            "• /translate — перевести текст\n"
            "• /menu — открыть меню кнопок\n"
            "• /info — показать данные о тебе\n"
            "• /stats — твоя статистика\n"
            "• /help — помощь и описание\n\n"
            "✨ Попробуй: <code>/translate en Привет, мир!</code>"
        )

        await message.answer(banner, parse_mode="HTML")

    except Exception as e:
        error_logger.error(f"Ошибка в /start: {e}")
        await message.answer("Произошла ошибка при обработке /start. Попробуйте снова.")

@dp.message(Command("menu"))
async def show_menu(message: types.Message):
    update_stats(message.from_user.id, "/menu")
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="🔄 Перевести текст", callback_data="translate_menu"),
            types.InlineKeyboardButton(text="🔹 О боте", callback_data="about_bot"),
            types.InlineKeyboardButton(text="👨‍💻 Разработчик", callback_data="developer"),
        ],
        [
            types.InlineKeyboardButton(text="🌐 GitHub", url="https://github.com/Inexis667")
        ]
    ])
    await message.answer("📋 Главное меню:", reply_markup=keyboard)

@dp.callback_query(F.data == "translate_menu")
async def translate_menu_callback(callback_query: types.CallbackQuery):
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🇬🇧 Английский", callback_data="lang_en")],
        [types.InlineKeyboardButton(text="🇩🇪 Немецкий", callback_data="lang_de")],
        [types.InlineKeyboardButton(text="🇫🇷 Французский", callback_data="lang_fr")],
        [types.InlineKeyboardButton(text="🇪🇸 Испанский", callback_data="lang_es")],
        [types.InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")],
    ])
    await callback_query.message.answer(
        "🌍 Выберите язык, на который хотите перевести текст:",
        reply_markup=keyboard
    )
    await callback_query.answer()

@dp.callback_query(F.data.startswith("lang_"))
async def translate_with_choice(callback_query: types.CallbackQuery):
    lang = callback_query.data.split("_")[1]
    await callback_query.message.answer(
        f"✏️ Теперь отправь текст для перевода на <b>{lang.upper()}</b>.\n\n"
        f"Пример:\n<code>Привет, как дела?</code>",
        parse_mode="HTML"
    )
    # Сохраняем язык пользователя, чтобы помнить, на какой язык переводить
    user_id = callback_query.from_user.id
    user_langs[user_id] = lang
    await callback_query.answer()

@dp.callback_query(F.data == "about_bot")
async def about_bot_callback(callback_query: types.CallbackQuery):
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu"),
            types.InlineKeyboardButton(text="⚙️ Функции", callback_data="bot_functions"),
        ]
    ])
    await callback_query.message.edit_text(
        "🤖 Я — Бот-Переводчик на Python (Aiogram)!\n"
        "Моя цель — помогать людям переводить текст с разных языков мира.",
        reply_markup=keyboard
    )

@dp.callback_query(F.data == "bot_functions")
async def bot_functions_callback(callback_query: types.CallbackQuery):
    text = (
        "⚙️ <b>Функции бота:</b>\n"
        "— Отвечает на команды /start, /help, /about, /info, /mood\n"
        "— Перевод текста по команде\n"
        "— Распознаёт фото и стикеры\n"
        "— Главное меню и информация 📋"
    )
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🔙 Назад", callback_data="about_bot")]
    ])
    await callback_query.message.edit_text(text, parse_mode="HTML", reply_markup=keyboard)

@dp.callback_query(F.data == "developer")
async def developer_callback(callback_query: types.CallbackQuery):
    await callback_query.answer("Разработчик: Аманшукур Алижан 👨‍💻", show_alert=True)

@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu_callback(callback_query: types.CallbackQuery):
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="🔹 О боте", callback_data="about_bot"),
            types.InlineKeyboardButton(text="👨‍💻 Разработчик", callback_data="developer"),
        ],
        [
            types.InlineKeyboardButton(text="🌐 GitHub", url="https://github.com/Inexis667")
        ]
    ])
    await callback_query.message.edit_text("📋 Главное меню:", reply_markup=keyboard)

@dp.message(Command("help"))
async def send_help(message: types.Message):
    update_stats(message.from_user.id, "/help")
    help_text = (
        "🆘 <b>Помощь по командам:</b>\n"
        "───────────────────────\n"
        "💬 /start — начать работу с ботом\n"
        "📋 /menu — открыть главное меню\n"
        "🈹 /translate &lt;язык&gt; &lt;текст&gt; — перевести текст\n"
        "📊 /stats — статистика использования\n"
        "👤 /info — информация о тебе\n"
        "💡 /about — о проекте\n"
        "🎭 /mood — настроение бота\n\n"
        "🌐 <b>Поддерживаемые языки:</b>\n"
        "<code>en</code> — Английский\n"
        "<code>ru</code> — Русский\n"
        "<code>de</code> — Немецкий\n"
        "<code>fr</code> — Французский\n"
        "<code>es</code> — Испанский\n"
        "<code>it</code> — Итальянский\n"
        "<code>zh</code> — Китайский\n\n"
        "💭 Просто напиши текст с вопросом — я отвечу!\n"
        "❓ Пример: <code>Как тебя зовут?</code>\n"
        "───────────────────────\n"
        "👨‍💻 Разработчик: <b>Аманшукур Алижан</b>\n"
        "📦 GitHub: <a href='https://github.com/Inexis667'>Inexis667</a>"
    )

    await message.answer(help_text, parse_mode="HTML", disable_web_page_preview=True)

@dp.message(Command("about"))
async def send_about(message: types.Message):
    update_stats(message.from_user.id, "/about")
    about_text = (
        "🤖 <b>О проекте</b>\n"
        "───────────────────────\n"
        "📘 Название: <b>Бот-Переводчик</b>\n"
        "🧩 Основан на: <code>Python + Aiogram + Deep Translator + gTTS</code>\n"
        "🎯 Назначение: мгновенный перевод текста и озвучка результата.\n\n"
        "⚙️ <b>Возможности:</b>\n"
        "• Перевод текста между десятками языков\n"
        "• Озвучивание перевода голосом\n"
        "• Меню с кнопками и выбор языка\n"
        "• Подсчёт статистики и активности\n"
        "• Реакции на фото, стикеры и вопросы\n\n"
        "👨‍💻 <b>Автор:</b> Аманшукур Алижан\n"
        "🔗 GitHub: <a href='https://github.com/Inexis667'>Inexis667</a>\n"
        "───────────────────────\n"
        "💬 <i>“Бот создан, чтобы сделать изучение языков проще и интереснее.”</i>"
    )

    await message.answer(about_text, parse_mode="HTML", disable_web_page_preview=True)

@dp.message(Command("info"))
async def send_info(message: types.Message):
        update_stats(message.from_user.id, "/info")
        user_id = message.from_user.id
        name = user_names.get(user_id, message.from_user.first_name)
        safe_name = html.escape(name)
        start_time = first_start_times.get(user_id, datetime.now().strftime("%d.%m.%Y %H:%M"))
        await message.answer(
            f"👤 <b>Информация о тебе:</b>\n\n"
            f"🪪 Имя: <b>{safe_name}</b>\n"
            f"🆔 Telegram ID: <code>{user_id}</code>\n"
            f"🕒 Первый запуск: {start_time}",
            parse_mode="HTML"
        )

@dp.message(Command("mood"))
async def send_mood(message: types.Message):
    update_stats(message.from_user.id, "/mood")
    moods = ["😊 Отличное!", "😐 Нормальное", "😴 Сонное", "🤩 Замечательное!", "🤔 Задумчивое"]
    await message.answer(f"🎭 Настроение бота: {random.choice(moods)}")

@dp.message(F.photo)
async def handle_photo(message: types.Message):
    print(f"[Фото] От {message.from_user.first_name}")
    await message.answer("Классная картинка! 📸")

@dp.message(F.sticker)
async def handle_sticker(message: types.Message):
    print(f"[Стикер] От {message.from_user.first_name}")
    await message.answer("Прикольный стикер! 😎")

@dp.message(Command("translate"))
async def translate_text(message: types.Message):
    update_stats(message.from_user.id, "/translate")
    try:
        parts = message.text.split(maxsplit=2)
        if len(parts) < 3:
            await message.answer("❌ Использование: /translate <язык> <текст>\nПример: /translate en Привет, мир!")
            return

        lang = parts[1].lower()
        text = parts[2]

        translated_text = GoogleTranslator(source="auto", target=lang).translate(text)
        await message.answer(f"🌍 Перевод ({lang.upper()}):\n{translated_text}")

        tts = gTTS(translated_text, lang=lang)
        file_path = "voice.mp3"
        tts.save(file_path)

        voice = FSInputFile(file_path)
        await message.answer_voice(voice)

        os.remove(file_path)

        info_logger.info(f"Перевод: '{text}' -> '{translated_text}' [{lang}]")

    except Exception as e:
        error_logger.error(f"Ошибка перевода: {e}")
        await message.answer("⚠️ Ошибка при переводе. Проверь язык и попробуй снова.")

@dp.message(Command("stats"))
async def show_stats(message: types.Message):
    user_id = str(message.from_user.id)
    if user_id not in stats:
        await message.answer("📊 У тебя пока нет статистики.")
        return

    user_data = stats[user_id]
    total_users = len(stats)
    total_messages = sum(u["messages"] for u in stats.values())

    commands = "\n".join([f"{cmd}: {count}" for cmd, count in user_data["commands"].items()])
    await message.answer(
        f"📈 <b>Твоя статистика:</b>\n"
        f"Сообщений: {user_data['messages']}\n"
        f"Использованные команды:\n{commands}\n\n"
        f"👥 Всего пользователей: {total_users}\n"
        f"💬 Всего сообщений: {total_messages}",
        parse_mode="HTML"
    )

@dp.message(F.text)
async def echo_message(message: types.Message):
    user_id = message.from_user.id
    text = message.text.strip()

    if user_id in user_langs:
        lang = user_langs[user_id]
        try:
            translated = GoogleTranslator(source='auto', target=lang).translate(text)
            await message.answer(f"✅ Перевод на {lang.upper()}:\n{translated}")
            info_logger.info(f"Перевод {text} -> {translated} [{lang}]")
        except Exception as e:
            await message.answer("⚠️ Ошибка при переводе.")
            error_logger.error(f"Ошибка при автопереводе: {e}")
        return

    if text.startswith("/"):
        await message.answer("❌ Неизвестная команда. Попробуйте /help")
        return

    if "?" in text:
        await message.answer("🤔 Хороший вопрос! Но я пока не знаю ответа.")
        return

    await message.answer("Чтобы перевести текст используйте: /translate <язык> <текст>\nНапример: /translate en Привет")

@dp.errors()
async def handle_error(event):
    error_logger.error(f"Ошибка: {event.exception}")

async def main():
    info_logger.info("Бот запущен.")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        error_logger.error(f"Критическая ошибка при запуске: {e}")
    finally:
        info_logger.info("Бот остановлен.")

if __name__ == "__main__":
    asyncio.run(main())
