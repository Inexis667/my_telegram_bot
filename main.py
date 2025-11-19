import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN не задан. Установите переменную окружения BOT_TOKEN.")


from aiogram import Bot, Dispatcher, types
from aiogram import F
from aiogram.filters import Command

from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
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
from aiogram.types import InlineQuery, InlineQueryResultArticle, InputTextMessageContent
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
    print(f"🔗 Инлайн-режим: @{me.username} текст")

user_translation_data = {}

class TranslationStates(StatesGroup):
    waiting_for_text = State()

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
user_translation_history = {}

def get_main_inline_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
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
        ]
    )

def get_language_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🎯 Популярные пары", callback_data="popular_pairs"),
                InlineKeyboardButton(text="🔧 Выбрать языки", callback_data="custom_translate")
            ],
            [
                InlineKeyboardButton(text="🇷🇺→🇬🇧 Рус→Англ", callback_data="pair_ru_en"),
                InlineKeyboardButton(text="🇬🇧→🇷🇺 Англ→Рус", callback_data="pair_en_ru")
            ],
            [
                InlineKeyboardButton(text="🇷🇺→🇩🇪 Рус→Нем", callback_data="pair_ru_de"),
                InlineKeyboardButton(text="🇩🇪→🇷🇺 Нем→Рус", callback_data="pair_de_ru")
            ],
            [
                InlineKeyboardButton(text="🇷🇺→🇫🇷 Рус→Фран", callback_data="pair_ru_fr"),
                InlineKeyboardButton(text="🇫🇷→🇷🇺 Фран→Рус", callback_data="pair_fr_ru")
            ],
            [
                InlineKeyboardButton(text="🇷🇺→🇦🇿 Рус→Азер", callback_data="pair_ru_az"),
                InlineKeyboardButton(text="🇦🇿→🇷🇺 Азер→Рус", callback_data="pair_az_ru")
            ],
            [
                InlineKeyboardButton(text="📜 История переводов", callback_data="translation_history")
            ],
            [
                InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")
            ]
        ]
    )

def get_source_language_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data="src_ru"),
                InlineKeyboardButton(text="🇬🇧 Английский", callback_data="src_en")
            ],
            [
                InlineKeyboardButton(text="🇩🇪 Немецкий", callback_data="src_de"),
                InlineKeyboardButton(text="🇫🇷 Французский", callback_data="src_fr")
            ],
            [
                InlineKeyboardButton(text="🇦🇿 Азербайджанский", callback_data="src_az"),
                InlineKeyboardButton(text="🇹🇷 Турецкий", callback_data="src_tr")
            ],
            [
                InlineKeyboardButton(text="🔍 Автоопределение", callback_data="src_auto")
            ],
            [
                InlineKeyboardButton(text="🔙 Назад", callback_data="translate_menu")
            ]
        ]
    )

def get_target_language_menu(source_lang):
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇷🇺 Русский", callback_data=f"target_{source_lang}_ru"),
                InlineKeyboardButton(text="🇬🇧 Английский", callback_data=f"target_{source_lang}_en")
            ],
            [
                InlineKeyboardButton(text="🇩🇪 Немецкий", callback_data=f"target_{source_lang}_de"),
                InlineKeyboardButton(text="🇫🇷 Французский", callback_data=f"target_{source_lang}_fr")
            ],
            [
                InlineKeyboardButton(text="🇦🇿 Азербайджанский", callback_data=f"target_{source_lang}_az"),
                InlineKeyboardButton(text="🇹🇷 Турецкий", callback_data=f"target_{source_lang}_tr")
            ],
            [
                InlineKeyboardButton(text="🔙 Назад", callback_data="custom_translate")
            ]
        ]
    )

def get_history_menu():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📜 Посмотреть историю", callback_data="view_history")],
            [InlineKeyboardButton(text="🗑️ Очистить историю", callback_data="clear_history")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="translate_menu")]
        ]
    )

def get_back_button():
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
        ]
    )


@dp.callback_query(F.data == "view_history")
async def view_history_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    if user_id not in user_translation_history or not user_translation_history[user_id]:
        await callback_query.message.edit_text(
            "📜 <b>История переводов пуста</b>\n\n"
            "Здесь будут сохраняться ваши последние переводы.",
            parse_mode="HTML",
            reply_markup=get_back_button()
        )
        return

    history_text = "📜 <b>Ваша история переводов:</b>\n\n"

    for i, record in enumerate(reversed(user_translation_history[user_id][-5:]), 1):
        history_text += f"<b>{i}.</b> [{record['direction']}] {record['timestamp']}\n"
        history_text += f"<code>{record['original'][:30]}...</code> → <code>{record['translated'][:30]}...</code>\n\n"

    await callback_query.message.edit_text(
        history_text,
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🗑️ Очистить историю", callback_data="clear_history")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="translate_menu")]
        ])
    )
    await callback_query.answer()

@dp.callback_query(F.data == "translation_history")
async def translation_history_callback(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(
        "📜 <b>История переводов</b>\n\n"
        "Здесь вы можете посмотреть или очистить историю ваших переводов.",
        parse_mode="HTML",
        reply_markup=get_history_menu()
    )
    await callback_query.answer()



@dp.callback_query(F.data == "clear_history")
async def clear_history_callback(callback_query: types.CallbackQuery):
    user_id = callback_query.from_user.id

    if user_id in user_translation_history:
        user_translation_history[user_id] = []

    await callback_query.message.edit_text(
        "🗑️ <b>История переводов очищена</b>",
        parse_mode="HTML",
        reply_markup=get_back_button()
    )
    await callback_query.answer()


@dp.inline_query()
async def inline_translator(inline_query: InlineQuery):
    print(f"🔍 ИНЛАЙН ЗАПРОС: '{inline_query.query}' от {inline_query.from_user.id}")
    query = inline_query.query.strip()

    # Если запрос пустой - показываем подсказку
    if not query:
        results = [
            InlineQueryResultArticle(
                id="help",
                title="🌍 Переводчик",
                description="Напишите текст для перевода",
                input_message_content=InputTextMessageContent(
                    message_text="🤖 <b>Translator from Alizhan</b>\n\n"
                                 "Используйте: язык текст\n"
                                 "Пример: en Привет мир\n\n"
                                 "Или просто текст для перевода на разные языки",
                    parse_mode="HTML"
                )
            )
        ]
        await inline_query.answer(results, cache_time=1)
        return

    # Парсим запрос: "язык текст" или просто текст
    parts = query.split(' ', 1)
    if len(parts) == 2 and len(parts[0]) == 2:  # формат "en текст"
        target_lang = parts[0].lower()
        text_to_translate = parts[1]

        # Перевод на один конкретный язык
        try:
            detected_lang = detect(text_to_translate)
            translated = GoogleTranslator(source=detected_lang, target=target_lang).translate(text_to_translate)

            lang_names = {
                "ru": "🇷🇺 Русский", "en": "🇬🇧 Английский", "de": "🇩🇪 Немецкий",
                "fr": "🇫🇷 Французский", "es": "🇪🇸 Испанский", "it": "🇮🇹 Итальянский",
                "zh": "🇨🇳 Китайский", "ja": "🇯🇵 Японский", "ko": "🇰🇷 Корейский"
            }

            results = [
                InlineQueryResultArticle(
                    id="1",
                    title=f"🌍 Перевод на {lang_names.get(target_lang, target_lang.upper())}",
                    description=f"{text_to_translate} → {translated}",
                    input_message_content=InputTextMessageContent(
                        message_text=f"🌍 <b>Перевод</b>\n\n"
                                     f"📥 <b>Исходный текст:</b>\n{text_to_translate}\n\n"
                                     f"📤 <b>Перевод ({lang_names.get(target_lang, target_lang.upper())}):</b>\n{translated}\n\n"
                                     f"<i>via Translator from Alizhan</i>",
                        parse_mode="HTML"
                    )
                )
            ]

        except Exception as e:
            results = [InlineQueryResultArticle(id="error", title="❌ Ошибка", description="Ошибка перевода",
                                                input_message_content=InputTextMessageContent(
                                                    message_text="❌ Ошибка перевода"))]

    else:
        # Просто текст - показываем готовые переводы на разные языки
        text_to_translate = query

        try:
            detected_lang = detect(text_to_translate)
            print(f"✅ Язык определен: {detected_lang}")

            # Популярные языки для перевода
            target_languages = ["en", "de", "fr", "es", "it", "ru"]

            results = []
            for lang in target_languages:
                if lang != detected_lang:  # не переводим на тот же язык
                    try:
                        translated = GoogleTranslator(source=detected_lang, target=lang).translate(text_to_translate)

                        lang_names = {
                            "ru": "🇷🇺 Русский", "en": "🇬🇧 Английский", "de": "🇩🇪 Немецкий",
                            "fr": "🇫🇷 Французский", "es": "🇪🇸 Испанский", "it": "🇮🇹 Итальянский"
                        }

                        results.append(InlineQueryResultArticle(
                            id=lang,
                            title=f"🌍 {lang_names.get(lang, lang.upper())}",
                            description=f"{text_to_translate} → {translated}",
                            input_message_content=InputTextMessageContent(
                                message_text=f"🌍 <b>Перевод на {lang_names.get(lang, lang.upper())}</b>\n\n"
                                             f"📥 <b>Исходный текст:</b>\n{text_to_translate}\n\n"
                                             f"📤 <b>Перевод:</b>\n{translated}\n\n"
                                             f"<i>via Translator from Alizhan</i>",
                                parse_mode="HTML"
                            )
                        ))
                    except Exception as e:
                        continue

            # Если нет результатов
            if not results:
                results = [InlineQueryResultArticle(id="error", title="❌ Ошибка", description="Не удалось перевести",
                                                    input_message_content=InputTextMessageContent(
                                                        message_text="❌ Ошибка перевода"))]

        except Exception as e:
            print(f"❌ ОШИБКА: {e}")
            results = [InlineQueryResultArticle(id="error", title="❌ Ошибка", description="Ошибка определения языка",
                                                input_message_content=InputTextMessageContent(
                                                    message_text="❌ Ошибка перевода"))]

    await inline_query.answer(results, cache_time=1)
    print(f"✅ Отправлено {len(results)} готовых переводов")


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
            "• 🔊 Текст в голосовые сообщения\n"
            "• 📜 История переводов\n"
            "• 🚀 <b>Инлайн-режим</b> - перевод в любом чате!\n\n"
            "📝 <b>Используйте /menu для доступа ко всем функциям</b>\n\n"
            "💡 <b>Попробуйте инлайн-режим:</b>\n"
            "Напишите <code>@TranslatorAlizh_bot Привет</code> в любом чате!"
        )

        await message.answer(banner, parse_mode="HTML")

    except Exception as e:
        error_logger.error(f"Ошибка в /start: {e}")
        await message.answer("Произошла ошибка при обработке /start. Попробуйте снова.")


@dp.message(Command("menu"))
@dp.message(F.text == "⚙️ Настройки")
async def show_menu(message: types.Message):
    update_stats(message.from_user.id, "/menu")

    await message.answer(
        "🎛️ <b>Главное меню</b>\n\n"
        "Выберите нужную функцию:\n\n"
        "🌍 <b>Переводчик</b> - перевод между языками\n"
        "📊 <b>Статистика</b> - ваша активность\n"
        "🎤 <b>Голос → Текст</b> - расшифровка аудио\n"
        "📸 <b>Текст с фото</b> - OCR из изображений\n"
        "🔊 <b>Текст → Голос</b> - синтез речи\n"
        "📈 <b>Топ пользователей</b> - рейтинг активности\n\n"
        "💡 <i>Используйте кнопки ниже:</i>",
        reply_markup=get_main_inline_menu(),
        parse_mode="HTML"
    )


@dp.callback_query(F.data == "translate_menu")
async def translate_menu_callback(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(
        "🌍 <b>Выберите язык перевода:</b>\n\n"
        "Или отправьте текст в формате:\n"
        "<code>язык текст</code>\n\n"
        "Пример: <code>en Привет мир</code>",
        parse_mode="HTML",
        reply_markup=get_language_menu()
    )
    await callback_query.answer()

@dp.callback_query(F.data.startswith("src_"))
async def set_source_language(callback_query: types.CallbackQuery, state: FSMContext):  # ← ДОБАВЬТЕ state: FSMContext
    source_lang = callback_query.data.split("_")[1]

    lang_names = {
        "auto": "🔍 Автоопределение", "ru": "🇷🇺 Русский", "en": "🇬🇧 Английский",
        "de": "🇩🇪 Немецкий", "fr": "🇫🇷 Французский", "es": "🇪🇸 Испанский",
        "az": "🇦🇿 Азербайджанский", "tr": "🇹🇷 Турецкий", "zh": "🇨🇳 Китайский"
    }

    await callback_query.message.edit_text(
        f"🌍 <b>Исходный язык:</b> {lang_names.get(source_lang, source_lang)}\n"
        f"Теперь выберите <b>целевой язык</b>:",
        parse_mode="HTML",
        reply_markup=get_target_language_menu(source_lang)
    )
    await callback_query.answer()


@dp.callback_query(F.data.startswith("target_"))
async def set_target_language(callback_query: types.CallbackQuery, state: FSMContext):  # ← ДОБАВЬТЕ state: FSMContext
    data = callback_query.data.split("_")
    source_lang = data[1]
    target_lang = data[2]

    print(f"🎯 Установка состояния перевода: {source_lang} → {target_lang}")

    lang_names = {
        "ru": "русский", "en": "английский", "de": "немецкий",
        "fr": "французский", "az": "азербайджанский", "tr": "турецкий"
    }

    await callback_query.message.edit_text(
        f"✏️ <b>Отправьте текст для перевода</b>\n\n"
        f"<b>Направление:</b> {lang_names.get(source_lang)} → {lang_names.get(target_lang)}\n\n"
        f"Пример:\n<code>Привет, как дела?</code>",
        parse_mode="HTML",
        reply_markup=get_back_button()
    )

    await state.update_data(
        source_lang=source_lang,
        target_lang=target_lang
    )
    await state.set_state(TranslationStates.waiting_for_text)

    print(f"✅ Состояние установлено: waiting_for_text")

    await callback_query.answer()


@dp.callback_query(F.data.startswith("pair_"))
async def translate_popular_pair(callback_query: types.CallbackQuery,
                                 state: FSMContext):  # ← ДОБАВЬТЕ state: FSMContext
    data = callback_query.data.split("_")
    source_lang = data[1]
    target_lang = data[2]

    print(f"🎯 Популярная пара: {source_lang} → {target_lang}")

    lang_names = {"ru": "русский", "en": "английский", "de": "немецкий", "fr": "французский", "az": "азербайджанский"}

    await callback_query.message.edit_text(
        f"✏️ <b>Отправьте текст для перевода</b>\n\n"
        f"<b>Направление:</b> {lang_names.get(source_lang)} → {lang_names.get(target_lang)}\n\n"
        f"Пример:\n<code>Привет, как дела?</code>",
        parse_mode="HTML",
        reply_markup=get_back_button()
    )

    await state.update_data(
        source_lang=source_lang,
        target_lang=target_lang
    )
    await state.set_state(TranslationStates.waiting_for_text)

    print(f"✅ Состояние установлено: waiting_for_text")

    await callback_query.answer()


@dp.callback_query(F.data.startswith("lang_"))
async def translate_with_choice(callback_query: types.CallbackQuery):
    lang = callback_query.data.split("_")[1]
    lang_names = {
        "en": "английский", "ru": "русский", "es": "испанский",
        "fr": "французский", "de": "немецкий", "it": "итальянский",
        "ja": "японский", "ko": "корейский", "zh": "китайский", "ar": "арабский"
    }

    await callback_query.message.edit_text(
        f"✏️ <b>Отправьте текст для перевода на {lang_names.get(lang, lang)}</b>\n\n"
        f"Пример:\n<code>Привет, как дела?</code>\n\n"
        f"💡 <i>Бот переведет ваш текст и покажет результат</i>",
        parse_mode="HTML",
        reply_markup=get_back_button()
    )
    await callback_query.answer()


@dp.callback_query(F.data == "stats_menu")
async def stats_menu_callback(callback_query: types.CallbackQuery):
    user_id = str(callback_query.from_user.id)
    user_data = stats.get(user_id, {"messages": 0, "commands": {}})

    total_commands = sum(user_data["commands"].values())
    top_commands = "\n".join([f"• {cmd}: {count}" for cmd, count in
                              sorted(user_data["commands"].items(), key=lambda x: x[1], reverse=True)[:3]])

    await callback_query.message.edit_text(
        f"📊 <b>Ваша статистика:</b>\n\n"
        f"💬 Сообщений: {user_data['messages']}\n"
        f"⚡ Команд: {total_commands}\n"
        f"👥 Всего пользователей: {len(stats)}\n\n"
        f"🏆 <b>Топ команд:</b>\n{top_commands}\n\n"
        f"<i>Используйте /stats для подробной статистики</i>",
        parse_mode="HTML",
        reply_markup=get_back_button()
    )
    await callback_query.answer()


@dp.callback_query(F.data == "top_users")
async def top_users_callback(callback_query: types.CallbackQuery):
    if not stats:
        await callback_query.message.edit_text(
            "📊 <b>Пока нет данных для топа</b>\n\n"
            "<i>Статистика появится после активного использования бота</i>",
            parse_mode="HTML",
            reply_markup=get_back_button()
        )
        return

    users = []
    for user_id, data in stats.items():
        commands_total = sum(data["commands"].values())
        messages_total = data["messages"]
        users.append((user_id, commands_total, messages_total))

    top_users = sorted(users, key=lambda x: (x[1], x[2]), reverse=True)[:5]

    medals = ["🥇", "🥈", "🥉", "🎖️", "🎖️"]
    text = "🏆 <b>Топ-5 активных пользователей:</b>\n\n"

    for i, (user_id, cmd, msg_count) in enumerate(top_users):
        text += f"{medals[i]} User — {cmd} команд, {msg_count} сообщений\n"

    await callback_query.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=get_back_button()
    )
    await callback_query.answer()


@dp.callback_query(F.data == "about_bot")
async def about_bot_callback(callback_query: types.CallbackQuery):
    total_messages = sum(u["messages"] for u in stats.values())
    total_commands = sum(sum(u["commands"].values()) for u in stats.values())

    await callback_query.message.edit_text(
        f"🤖 <b>Translator from Alizhan</b>\n\n"
        f"📅 <b>Версия:</b> 2.0 Professional\n"
        f"👨‍💻 <b>Разработчик:</b> Alizhan\n"
        f"🐍 <b>Технологии:</b> Python, Aiogram, AI\n\n"
        f"📈 <b>Статистика бота:</b>\n"
        f"• Пользователей: {len(stats)}\n"
        f"• Сообщений: {total_messages}\n"
        f"• Команд: {total_commands}\n\n"
        f"⭐ <b>Ключевые возможности:</b>\n"
        f"• Поддержка 100+ языков перевода\n"
        f"• Высокая точность распознавания\n"
        f"• Быстрая обработка запросов\n"
        f"• Удобный интерфейс\n\n"
        f"💬 <i>По вопросам и предложениям используйте /help</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [
                InlineKeyboardButton(text="⚙️ Функции", callback_data="bot_functions"),
                InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")
            ]
        ])
    )
    await callback_query.answer()


@dp.callback_query(F.data == "bot_functions")
async def bot_functions_callback(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(
        "⚙️ <b>Все функции бота:</b>\n\n"
        "🌍 <b>Переводчик:</b>\n"
        "• Поддержка 100+ языков\n"
        "• Быстрый и точный перевод\n"
        "• Удобный выбор языка\n\n"
        "📊 <b>Аналитика:</b>\n"
        "• Личная статистика\n"
        "• Топ активных пользователей\n"
        "• Анализ использования\n\n"
        "🎤 <b>Голосовые функции:</b>\n"
        "• Голос → Текст (Speech-to-Text)\n"
        "• Текст → Голос (Text-to-Speech)\n\n"
        "📸 <b>Работа с изображениями:</b>\n"
        "• Распознавание текста с фото\n"
        "• Поддержка разных форматов\n\n"
        "🎛️ <b>Интерфейс:</b>\n"
        "• Удобное меню\n"
        "• Быстрый доступ к функциям\n"
        "• Простая навигация",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔙 Назад", callback_data="about_bot")]
        ])
    )
    await callback_query.answer()


@dp.callback_query(F.data == "voice_to_text")
async def voice_to_text_callback(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(
        "🎤 <b>Голос → Текст</b>\n\n"
        "Отправьте голосовое сообщение или аудиофайл, и я преобразую его в текст.\n\n"
        "📝 <b>Поддерживаемые форматы:</b>\n"
        "• Голосовые сообщения Telegram\n"
        "• Аудиофайлы (MP3, WAV, OGG)\n"
        "• Видеосообщения\n\n"
        "💡 <i>Просто отправьте голосовое сообщение - бот автоматически его обработает</i>",
        parse_mode="HTML",
        reply_markup=get_back_button()
    )
    await callback_query.answer()


@dp.callback_query(F.data == "text_from_photo")
async def text_from_photo_callback(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(
        "📸 <b>Текст с фото</b>\n\n"
        "Отправьте изображение с текстом, и я распознаю его.\n\n"
        "📝 <b>Поддерживаемые форматы:</b>\n"
        "• Фотографии (JPG, PNG)\n"
        "• Сканы документов\n"
        "• Скриншоты с текстом\n\n"
        "💡 <i>Просто отправьте изображение - бот автоматически распознает текст</i>",
        parse_mode="HTML",
        reply_markup=get_back_button()
    )
    await callback_query.answer()


@dp.callback_query(F.data == "text_to_voice")
async def text_to_voice_callback(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(
        "🔊 <b>Текст → Голос</b>\n\n"
        "Отправьте текст, и я преобразую его в голосовое сообщение.\n\n"
        "📝 <b>Возможности:</b>\n"
        "• Поддержка разных языков\n"
        "• Естественное звучание\n"
        "• Быстрое преобразование\n\n"
        "💡 <i>Просто отправьте текст - бот ответит голосовым сообщением</i>",
        parse_mode="HTML",
        reply_markup=get_back_button()
    )
    await callback_query.answer()


@dp.callback_query(F.data == "help_menu")
async def help_menu_callback(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(
        "🆘 <b>Справка и поддержка</b>\n\n"
        "🔹 <b>Основные команды:</b>\n"
        "/start - Запуск бота\n"
        "/menu - Главное меню\n"
        "/help - Эта справка\n\n"
        "🔹 <b>Функциональные команды:</b>\n"
        "/translate - Переводчик текста\n"
        "/stats - Ваша статистика\n"
        "/top - Топ пользователей\n"
        "/about - Информация о боте\n\n"
        "🔹 <b>Быстрый доступ:</b>\n"
        "• Используйте Reply-кнопки внизу\n"
        "• Или Inline-меню через /menu\n\n"
        "❓ <b>Частые вопросы:</b>\n"
        "• Как перевести текст? - Используйте Переводчик\n"
        "• Где статистика? - Команда /stats\n"
        "• Не работает функция? - Перезапустите /start\n\n"
        "💬 <i>Для связи с разработчиком используйте кнопку ниже</i>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="👨‍💻 Связь с разработчиком", callback_data="developer")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
        ])
    )
    await callback_query.answer()


@dp.callback_query(F.data == "developer")
async def developer_callback(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(
        "👨‍💻 <b>Разработчик</b>\n\n"
        "💼 <b>Имя:</b> Аманшукур Алижан\n"
        "🎓 <b>Специализация:</b> Python разработка\n"
        "🤖 <b>Направление:</b> Telegram боты, AI\n\n"
        "📧 <b>Контакты:</b>\n"
        "• GitHub: https://github.com/Inexis667\n"
        "• Telegram: @Inexis667\n\n"
        "💡 <b>О проекте:</b>\n"
        "Этот бот создан как демонстрация возможностей\n"
        "Python и библиотеки Aiogram для создания\n"
        "многофункциональных Telegram ботов.",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🌐 GitHub", url="https://github.com/Inexis667")],
            [InlineKeyboardButton(text="🔙 Назад", callback_data="back_to_menu")]
        ])
    )
    await callback_query.answer()


@dp.callback_query(F.data == "back_to_menu")
async def back_to_menu_callback(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(
        "🎛️ <b>Главное меню</b>\n\n"
        "Выберите нужную функцию:",
        reply_markup=get_main_inline_menu(),
        parse_mode="HTML"
    )
    await callback_query.answer()


@dp.callback_query(F.data == "popular_pairs")
async def popular_pairs_callback(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(
        "🎯 <b>Популярные языковые пары</b>\n\n"
        "Выберите направление перевода:",
        parse_mode="HTML",
        reply_markup=get_language_menu()
    )
    await callback_query.answer()


@dp.callback_query(F.data == "custom_translate")
async def custom_translate_callback(callback_query: types.CallbackQuery):
    await callback_query.message.edit_text(
        "🔧 <b>Расширенный выбор языков</b>\n\n"
        "Сначала выберите <b>исходный язык</b>:",
        parse_mode="HTML",
        reply_markup=get_source_language_menu()
    )
    await callback_query.answer()


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
        "🚀 <b>Инлайн-режим:</b>\n"
        "Напишите <code>@TranslatorAlizh_bot текст</code> в любом чате\n"
        "Или <code>@TranslatorAlizh_bot en текст</code> для конкретного языка\n\n"
        "🔹 <b>Быстрый доступ через кнопки:</b>\n"
        "• Используйте меню внизу экрана\n"
        "• Все функции в одном месте\n\n"
        "📝 <b>Примеры использования:</b>\n"
        "<code>/translate en Привет мир</code>\n"
        "<code>@TranslatorAlizh_bot de Hello</code>\n"
        "<code>Отправьте голосовое сообщение</code>\n\n"
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

@dp.message(F.text.startswith("/"))
async def unknown_command_handler(message: types.Message):
    await message.answer("❌ Неизвестная команда. Попробуйте /help")

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

@dp.message(F.text & ~F.command())
async def handle_all_text_messages(message: types.Message, state: FSMContext):
    user_id = message.from_user.id
    current_state = await state.get_state()
    text = message.text.strip()

    if current_state == TranslationStates.waiting_for_text:
        print("🎯 Состояние: waiting_for_text - обрабатываем перевод")

        user_data = await state.get_data()
        source_lang = user_data.get('source_lang')
        target_lang = user_data.get('target_lang')

        print(f"🌍 Языки перевода: {source_lang} → {target_lang}")

        try:
            if source_lang == "auto":
                try:
                    detected_lang = detect(text)
                    source_lang = detected_lang
                except Exception as e:
                    source_lang = 'auto'

            translated = GoogleTranslator(
                source=source_lang if source_lang != "auto" else 'auto',
                target=target_lang
            ).translate(text)

            lang_names = {
                "ru": "русский", "en": "английский", "de": "немецкий",
                "fr": "французский", "az": "азербайджанский", "es": "испанский",
                "tr": "турецкий", "zh": "китайский", "auto": "автоопределение"
            }

            source_display = lang_names.get(source_lang, source_lang)
            if source_lang == "auto":
                source_display = "автоопределение"

            await message.answer(
                f"🌍 <b>Результат перевода:</b>\n\n"
                f"📥 <b>Исходный текст ({source_display}):</b>\n<code>{text}</code>\n\n"
                f"📤 <b>Перевод ({lang_names.get(target_lang, target_lang)}):</b>\n<code>{translated}</code>\n\n"
                f"💡 <i>Для нового перевода используйте меню</i>",
                parse_mode="HTML",
                reply_markup=get_main_inline_menu()
            )

            update_stats(user_id, "translate")

            translation_record = {
                "original": message.text,
                "translated": translated,
                "direction": f"{source_lang}→{target_lang}",
                "timestamp": datetime.now().strftime("%d.%m.%Y %H:%M")
            }

            if user_id not in user_translation_history:
                user_translation_history[user_id] = []

            user_translation_history[user_id].append(translation_record)
            if len(user_translation_history[user_id]) > 10:
                user_translation_history[user_id] = user_translation_history[user_id][-10:]

        except Exception as e:
            await message.answer(
                f"❌ <b>Ошибка перевода</b>\n\n"
                f"Попробуйте еще раз или выберите другой язык.",
                parse_mode="HTML",
                reply_markup=get_main_inline_menu()
            )

        await state.clear()

    elif user_id in user_langs:
        lang = user_langs[user_id]
        try:
            translated = GoogleTranslator(source='auto', target=lang).translate(text)
            await message.answer(f"✅ Перевод на {lang.upper()}:\n{translated}")
            info_logger.info(f"Перевод {text} -> {translated} [{lang}]")
        except Exception as e:
            await message.answer("⚠️ Ошибка при переводе.")
            error_logger.error(f"Ошибка при автопереводе: {e}")

    else:
        await message.answer(
            "🤖 <b>Я понимаю команды и переводы</b>\n\n"
            "Для перевода используйте меню: /menu\n"
            "Для справки: /help",
            parse_mode="HTML",
            reply_markup=get_main_inline_menu()
        )

if __name__ == "__main__":
    dp.startup.register(on_startup)
    asyncio.run(main())