import os
from dotenv import load_dotenv

print("📁 Текущая папка:", os.getcwd())
print("📋 Файлы в папке:", [f for f in os.listdir(".") if not f.startswith(".")])

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
print("🔑 BOT_TOKEN:", "ЕСТЬ" if BOT_TOKEN else "НЕТ")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан. Установите переменную окружения BOT_TOKEN.")



from aiogram import Bot, Dispatcher, types
from aiogram import F
from aiogram.filters import Command

from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.filters import StateFilter

from aiogram.types import FSInputFile
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from stats import update_stats, stats, get_user_stats
import html
import logging
from gtts import gTTS
import asyncio
from datetime import datetime
import random
import pytesseract
import speech_recognition as sr
from pydub import AudioSegment
from PIL import Image
from langdetect import detect, LangDetectException
from deep_translator import GoogleTranslator
import time

pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

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

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

async def on_startup(bot: Bot):
    me = await bot.get_me()
    print(f"🤖 {me.first_name} запущен!")

async def log_api_call(name: str, coro):
    start_time = time.time()
    try:
        result = await coro
        duration = time.time() - start_time
        if duration > 1:
            info_logger.warning(f"Долгий ответ API '{name}': {duration:.2f} сек")
        else:
            info_logger.info(f"Успешный запрос '{name}' за {duration:.2f} сек")
        return result
    except Exception as e:
        error_logger.error(f"Ошибка в API '{name}': {e}")
        raise

users = set()
first_start_times = {}
user_names = {}
user_langs = {}
user_history = {}

class TranslationStates(StatesGroup):
    waiting_for_text = State()

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
            "👋 <b>Добро пожаловать в Translator from Alizhan!</b>\n\n"
            "🚀 <i>Многофункциональный бот для работы с текстом и не только</i>\n\n"
            "✨ <b>Основные возможности:</b>\n"
            "• 🌍 Перевод между 100+ языками\n"
            "• 📊 Статистика и аналитика\n"
            "• 🎤 Конвертация голоса в текст\n"
            "• 📸 Распознавание текста с фото\n"
            "• 🔊 Текст в голосовые сообщения\n\n"
            "📝 <b>Используйте /menu для доступа ко всем функциям</b>"
        )

        await message.answer(banner, parse_mode="HTML")

    except Exception as e:
        error_logger.error(f"Ошибка в /start: {e}")
        await message.answer("Произошла ошибка при обработке /start. Попробуйте снова.")

def get_main_reply_menu():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🌍 Переводчик"), KeyboardButton(text="📊 Статистика")],
            [KeyboardButton(text="🎤 Голос → Текст"), KeyboardButton(text="📸 Текст с фото")],
            [KeyboardButton(text="🔊 Текст → Голос"), KeyboardButton(text="ℹ️ О боте")],
            [KeyboardButton(text="🆘 Помощь"), KeyboardButton(text="⚙️ Настройки")]
        ],
        resize_keyboard=True,
        input_field_placeholder="Выберите действие..."
    )

def get_main_inline_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌍 Переводчик", callback_data="translate_menu"),
            InlineKeyboardButton(text="📊 Статистика", callback_data="stats_menu")
        ],
        [
            InlineKeyboardButton(text="🎤 Голос → Текст", callback_data="voice_to_text"),
            InlineKeyboardButton(text="📸 Текст с фото", callback_data="text_from_photo")
        ],
        [
            InlineKeyboardButton(text="🔊 Текст → Голос", callback_data="text_to_voice"),
            InlineKeyboardButton(text="📈 Топ пользователей", callback_data="top_users")
        ],
        [
            InlineKeyboardButton(text="ℹ️ О боте", callback_data="about_bot"),
            InlineKeyboardButton(text="🆘 Помощь", callback_data="help_menu")
        ],
        [
            InlineKeyboardButton(text="👨‍💻 Разработчик", callback_data="developer"),
            InlineKeyboardButton(text="🌐 GitHub", url="https://github.com/Inexis667")
        ]
    ])

def get_language_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🇬🇧 Английский", callback_data="lang_en"),
            InlineKeyboardButton(text="🇷🇺 Русский", callback_data="lang_ru")
        ],
        [
            InlineKeyboardButton(text="🇪🇸 Испанский", callback_data="lang_es"),
            InlineKeyboardButton(text="🇫🇷 Французский", callback_data="lang_fr")
        ],
        [
            InlineKeyboardButton(text="🇩🇪 Немецкий", callback_data="lang_de"),
            InlineKeyboardButton(text="🇮🇹 Итальянский", callback_data="lang_it")
        ],
        [
            InlineKeyboardButton(text="🇯🇵 Японский", callback_data="lang_ja"),
            InlineKeyboardButton(text="🇰🇷 Корейский", callback_data="lang_ko")
        ],
        [
            InlineKeyboardButton(text="🇨🇳 Китайский", callback_data="lang_zh"),
            InlineKeyboardButton(text="🇦🇪 Арабский", callback_data="lang_ar")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")
        ]
    ])

def get_settings_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Уведомления", callback_data="settings_notifications"),
            InlineKeyboardButton(text="🎨 Тема", callback_data="settings_theme")
        ],
        [
            InlineKeyboardButton(text="🌍 Язык интерфейса", callback_data="settings_language"),
            InlineKeyboardButton(text="⚡ Автоперевод", callback_data="settings_auto")
        ],
        [
            InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")
        ]
    ])

def get_back_button():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
    ])

@dp.message(Command(commands=["help"]))
async def send_help(message: types.Message):
    update_stats(message.from_user.id, "/help")
    help_text = (
        "🆘 <b>Справка по командам</b>\n\n"
        "🔹 <b>Основные команды:</b>\n"
        "/start - Запуск бота\n"
        "/menu - Главное меню\n"
        "/help - Эта справка\n\n"
        "🔹 <b>Функциональные команды:</b>\n"
        "/translate - Переводчик текста\n"
        "/stats - Ваша статистика\n"
        "/top - Топ пользователей\n"
        "/about - Информация о боте\n\n"
        "🔹 <b>Быстрый доступ через кнопки:</b>\n"
        "• Используйте меню внизу экрана\n"
        "• Все функции в одном месте\n\n"
        "📝 <b>Примеры использования:</b>\n"
        "<code>/translate en Привет мир</code>\n"
        "<code>Отправьте голосовое сообщение</code>\n"
        "<code>Отправьте фото с текстом</code>\n\n"
        "❓ <i>Если что-то не работает - перезапустите бота /start</i>"
    )

    await message.answer(help_text, parse_mode="HTML", disable_web_page_preview=True)

@dp.message(Command(commands=["about"]))
async def send_about(message: types.Message):
    update_stats(message.from_user.id, "/about")
    about_text = (
        "🤖 <b>Translator from Alizhan</b>\n\n"
        "📅 <b>Версия:</b> 2.0\n"
        "👨‍💻 <b>Разработчик:</b> Alizhan\n"
        "🐍 <b>Технологии:</b> Python, Aiogram, AI\n\n"
        "⭐ <b>Ключевые возможности:</b>\n"
        "• Поддержка 100+ языков перевода\n"
        "• Высокая точность распознавания\n"
        "• Быстрая обработка запросов\n"
        "• Статистика использования\n"
        "• Удобный интерфейс\n\n"
        "🛠️ <b>Используемые API:</b>\n"
        "• Google Translate API\n"
        "• SpeechRecognition\n"
        "• Tesseract OCR\n"
        "• gTTS (Text-to-Speech)\n\n"
        "📈 <b>Статистика бота:</b>\n"
        f"• Пользователей: {len(stats)}\n"
        f"• Сообщений: {sum(u['messages'] for u in stats.values())}\n\n"
        "💬 <i>По вопросам и предложениям: /help</i>"
    )

    await message.answer(about_text, parse_mode="HTML", disable_web_page_preview=True)

@dp.message(Command(commands=["info"]))
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

@dp.message(Command(commands=["mood"]))
async def send_mood(message: types.Message):
    update_stats(message.from_user.id, "/mood")
    moods = ["😊 Отличное!", "😐 Нормальное", "😴 Сонное", "🤩 Замечательное!", "🤔 Задумчивое"]
    await message.answer(f"🎭 Настроение бота: {random.choice(moods)}")

@dp.message(Command(commands=["translate"]))
async def translate_text(message: types.Message):
    update_stats(message.from_user.id, "/translate")
    start_time = datetime.now()
    file_path = None

    try:
        text_full = (message.text or "").strip()

        parts = text_full.split(maxsplit=2)
        if len(parts) == 1:
            await message.answer("❌ Использование: /translate <язык> <текст>\nПример: /translate en Привет, мир!")
            return

        if len(parts) == 2:
            maybe_text = parts[1].strip()
            if not maybe_text:
                await message.answer("❌ Текст пустой.")
                return

            try:
                src_lang = detect(maybe_text)
                if src_lang.startswith("ru"):
                    lang = "en"
                else:
                    lang = "ru"
            except LangDetectException:
                lang = "en"
            text = maybe_text

        else:
            lang = parts[1].lower().strip()
            text = parts[2].strip()

        if not text:
            await message.answer("❌ Текст для перевода пустой.")
            return

        if len(text) > 4000:
            await message.answer("⚠️ Текст слишком длинный — сократи до 4000 символов.")
            return

        try:
            translated_text = GoogleTranslator(source="auto", target=lang).translate(text)
        except Exception as e:
            error_logger.error(f"Ошибка вызова GoogleTranslator: {e}")
            await message.answer("⚠️ Ошибка перевода: проверь код языка (например en, ru) или попробуй позже.")
            return

        await message.answer(f"🌍 Перевод ({lang.upper()}):\n{translated_text}")

        user_id = message.from_user.id
        if user_id not in user_history:
            user_history[user_id] = []

        user_history[user_id].append({
            "original": text,
            "translated": translated_text,
            "lang": lang,
            "time": datetime.now().strftime("%H:%M:%S %d.%m.%Y")
        })
        if len(user_history[user_id]) > 5:
            user_history[user_id] = user_history[user_id][-5:]

        info_logger.info(f"Перевод: '{text}' -> '{translated_text}' [{lang}]")

        try:
            if lang and translated_text.strip():
                file_path = f"voice_{message.from_user.id}_{int(datetime.now().timestamp())}.mp3"
                tts = gTTS(translated_text, lang=lang)
                tts.save(file_path)
                voice = FSInputFile(file_path)
                await message.answer_voice(voice)
        except Exception as e:
            error_logger.error(f"Ошибка при создании озвучки: {e}")

    except Exception as e:
        error_logger.error(f"Ошибка в /translate: {e}")
        await message.answer("⚠️ Внутренняя ошибка при обработке запроса. Попробуй ещё раз.")

    finally:
        try:
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
        except Exception as e:
            error_logger.error(f"Не удалось удалить временный файл: {e}")

        elapsed = (datetime.now() - start_time).total_seconds()
        if elapsed > 1:
            info_logger.warning(
                f"⚠️ Медленный ответ: {elapsed:.2f} сек при /translate пользователем {message.from_user.id}"
            )

@dp.message(Command(commands=["ptrans"]))
async def photo_translate_command(message: types.Message):
    await message.reply("📸 Отправь фото с текстом, который нужно перевести.")


@dp.message(lambda msg: msg.photo)
async def handle_photo(message: types.Message):
    user_id = message.from_user.id
    photo = message.photo[-1]
    file = await bot.get_file(photo.file_id)
    file_path = file.file_path
    file_name = f"photo_{user_id}.jpg"
    await bot.download_file(file_path, file_name)

    anim_msg = await message.reply("🧐 Распознаём текст... ⏳")

    spinners = ["⏳", "⌛", "🔄", "🌀"]
    for spin in spinners:
        await asyncio.sleep(0.4)
        try:
            await anim_msg.edit_text(f"🧐 Распознаём текст... {spin}")
        except Exception:
            pass

    try:
        from PIL import ImageEnhance, ImageFilter

        # 🔹 Обработка изображения
        image = Image.open(file_name).convert("L")
        enhancer = ImageEnhance.Contrast(image)
        image = enhancer.enhance(2.5)
        image = image.filter(ImageFilter.MedianFilter(size=3))
        image = image.filter(ImageFilter.SHARPEN)
        image = image.point(lambda p: 255 if p > 150 else 0)

        text = pytesseract.image_to_string(
            image,
            lang="rus+eng+deu+fra+spa+ita+chi_sim+jpn",
            config="--oem 3 --psm 6"
        ).strip()

        if not text:
            await anim_msg.edit_text("😕 Не удалось распознать текст на изображении.")
            return

        clean_text = ''.join(ch for ch in text if ch.isalpha() or ch.isspace())
        try:
            src_lang = detect(clean_text)
        except Exception:
            src_lang = "auto"

        if any("а" <= ch.lower() <= "я" for ch in text):
            src_lang = "ru"

        main_lang = "ru"
        fallback_lang = "en"
        target_lang = fallback_lang if src_lang == main_lang else main_lang

        translated = GoogleTranslator(source=src_lang, target=target_lang).translate(text)

        # 🔹 Обновляем статистику после успешного перевода фото
        update_stats(user_id, "/ptrans_translate")

        await anim_msg.edit_text(
            f"✅ <b>Распознанный язык:</b> {src_lang.upper()}\n\n"
            f"📜 <b>Распознанный текст:</b>\n<blockquote>{text}</blockquote>\n\n"
            f"🌍 <b>Перевод ({target_lang.upper()}):</b>\n<blockquote>{translated}</blockquote>",
            parse_mode="HTML"
        )

    except Exception as e:
        await anim_msg.edit_text(f"⚠️ Ошибка при обработке изображения: {e}")


@dp.message(Command("vtrans"))
async def start_vtrans(message: types.Message):
    update_stats(message.from_user.id, "/vtrans")
    await message.reply("🎤 Отправь голосовое сообщение на русском, я переведу его на английский.")

@dp.message(lambda msg: msg.voice or msg.audio)
async def handle_voice(message: types.Message):
    user_id = message.from_user.id
    file_path_ogg = f"voice_{user_id}.ogg"
    file_path_wav = f"voice_{user_id}.wav"
    tts_path = f"translated_{user_id}.mp3"

    try:
        voice = message.voice or message.audio
        file_info = await bot.get_file(voice.file_id)
        await bot.download_file(file_info.file_path, file_path_ogg)

        sound = AudioSegment.from_file(file_path_ogg)
        sound.export(file_path_wav, format="wav")

        recognizer = sr.Recognizer()
        with sr.AudioFile(file_path_wav) as source:
            audio_data = recognizer.record(source)

        try:
            text = recognizer.recognize_google(audio_data, language="ru-RU")
        except sr.UnknownValueError:
            await message.reply("😕 Не удалось распознать речь. Попробуй сказать чётче.")
            return
        except sr.RequestError as e:
            await message.reply(f"⚠️ Ошибка при обращении к Google Speech API: {e}")
            return

        if not text.strip():
            await message.reply("⚠️ Не удалось получить текст из аудио.")
            return

        try:
            translated = GoogleTranslator(source="ru", target="en").translate(text)
        except Exception as e:
            await message.reply(f"⚠️ Ошибка перевода: {e}")
            return

        await message.reply(
            f"🎧 <b>Распознанный текст:</b>\n<blockquote>{text}</blockquote>\n\n"
            f"🌍 <b>Перевод (EN):</b>\n<blockquote>{translated}</blockquote>",
            parse_mode="HTML"
        )

        try:
            gTTS(translated, lang="en").save(tts_path)
            await message.reply_voice(FSInputFile(tts_path))
        except Exception as e:
            error_logger.error(f"Ошибка при озвучке /vtrans: {e}")

    except Exception as e:
        error_logger.error(f"Ошибка обработки голосового: {e}")
        await message.reply(f"⚠️ Произошла ошибка при обработке аудио: {e}")
    finally:
        for f in [file_path_ogg, file_path_wav, tts_path]:
            if f and os.path.exists(f):
                try:
                    os.remove(f)
                except Exception:
                    pass


@dp.message(Command("stats"))
async def show_stats(message: types.Message):

    update_stats(message.from_user.id, "/stats")

    user_id = str(message.from_user.id)
    user_data = stats.get(user_id, {"messages": 0, "commands": {}})

    total_users = len(stats)
    total_messages = sum(u["messages"] for u in stats.values())

    cmds = sorted(user_data["commands"].items(), key=lambda x: x[1], reverse=True)
    top_commands = "\n".join([f"{cmd}: {count}" for cmd, count in cmds[:5]]) if cmds else "— нет данных —"

    response = (
        f"📈 <b>Твоя статистика:</b>\n"
        f"Сообщений: {user_data['messages']}\n"
        f"Топ-5 команд:\n{top_commands}\n\n"
        f"👥 Пользователей: {total_users}\n"
        f"💬 Всего сообщений: {total_messages}"
    )

    await message.answer(response, parse_mode="HTML")


@dp.message(Command("top"))
async def show_top(message: types.Message):
    if not stats:
        await message.answer("📊 Нет данных.")
        return

    update_stats(message.from_user.id, "/top")

    users = []
    for user_id, data in stats.items():
        commands_total = sum(data["commands"].values())
        messages_total = data["messages"]
        users.append((user_id, commands_total, messages_total))

    top_users = sorted(users, key=lambda x: (x[1], x[2]), reverse=True)[:5]

    medals = ["🥇", "🥈", "🥉", "🏅", "🎖️"]
    text = "🏆 <b>Топ-5 активных пользователей:</b>\n\n"

    for i, (user_id, cmd, msg_count) in enumerate(top_users):
        text += f"{medals[i]} <a href='tg://user?id={user_id}'>User</a> — {cmd} команд, {msg_count} сообщений\n"

    await message.answer(text, parse_mode="HTML")


@dp.message(Command(commands=["history"]))
async def show_history(message: types.Message):
    update_stats(message.from_user.id, "/history")
    user_id = message.from_user.id
    history = user_history.get(user_id)

    if not history or len(history) == 0:
        await message.answer("📂 У тебя пока нет истории переводов.")
        return

    text_lines = ["📜 <b>Твоя история переводов (последние 5):</b>\n"]
    for i, item in enumerate(reversed(history), 1):
        text_lines.append(
            f"{i}. <b>{item['time']}</b>\n"
            f"🌍 Язык: <code>{item['lang']}</code>\n"
            f"📝 Оригинал: <i>{item['original']}</i>\n"
            f"🔊 Перевод: <b>{item['translated']}</b>\n"
            "───────────────────────"
        )

    text_lines.append("\n❌ Чтобы очистить историю, введи /clear_history")
    await message.answer("\n".join(text_lines), parse_mode="HTML")

@dp.message(Command("clear_history"))
async def clear_history(message: types.Message):
    update_stats(message.from_user.id, "/clear_history")
    user_id = message.from_user.id
    user_history[user_id] = []
    await message.answer("🗑️ Ваша история переводов очищена.")

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

@dp.message(F.text.startswith("/"))
async def unknown_command_handler(message: types.Message):
    await message.answer("❌ Неизвестная команда. Попробуйте /help")

    # Хендлер для обычных сообщений (не команд)
@dp.message()
async def non_command_handler(message: types.Message):
    await message.answer("🤖 Я понимаю только команды. Напишите /help для списка команд.")

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
    dp.startup.register(on_startup)
    asyncio.run(main())

