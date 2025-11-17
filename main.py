from aiogram.types import FSInputFile
import html
import logging
from gtts import gTTS
import asyncio
from datetime import datetime
import random

from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
import pytesseract
import speech_recognition as sr
from pydub import AudioSegment
from PIL import Image
from langdetect import detect, LangDetectException
from aiogram import F
from deep_translator import GoogleTranslator
import time
import os
import json

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

BOT_TOKEN = os.getenv("BOT_TOKEN", "8285221368:AAGeHopGEPs22eZfXbA-U_-Fdn9tqpeuDwM")
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан. Установите переменную окружения BOT_TOKEN.")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

STATS_FILE = "stats.json"
stats = {}

def load_stats():
    global stats
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE, "r", encoding="utf-8") as f:
                stats = json.load(f)
        except:
            stats = {}
    else:
        stats = {}

def save_stats():
    with open(STATS_FILE, "w", encoding="utf-8") as f:
        json.dump(stats, f, ensure_ascii=False, indent=4)

def update_stats(user_id, command):
    user_id = str(user_id)

    if user_id not in stats:
        stats[user_id] = {"messages": 0, "commands": {}}

    stats[user_id]["messages"] += 1
    stats[user_id]["commands"][command] = stats[user_id]["commands"].get(command, 0) + 1

    save_stats()

# Загружаем статистику при старте
load_stats()

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

@dp.message(Command(commands=["help"]))
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

@dp.message(Command(commands=["about"]))
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

    if user_id not in stats:
        await message.answer("📊 У тебя пока нет статистики.")
        return

    user_data = stats[user_id]

    total_users = len(stats)
    total_messages = sum(u["messages"] for u in stats.values())

    cmds = sorted(user_data["commands"].items(), key=lambda x: x[1], reverse=True)
    top_commands = "\n".join([f"{cmd}: {count}" for cmd, count in cmds[:5]]) if cmds else "— нет данных —"

    await message.answer(
        f"📈 <b>Твоя статистика:</b>\n"
        f"Сообщений: {user_data['messages']}\n"
        f"Топ-5 команд:\n{top_commands}\n\n"
        f"👥 Пользователей: {total_users}\n"
        f"💬 Сообщений всего: {total_messages}",
        parse_mode="HTML"
    )

@dp.message(Command("top"))
async def show_top(message: types.Message):
    update_stats(message.from_user.id, "/top")

    if not stats:
        await message.answer("📊 Нет данных.")
        return

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
