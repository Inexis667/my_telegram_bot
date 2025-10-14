from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram import F
import asyncio
import random
from datetime import datetime
BOT_TOKEN = "8285221368:AAGeHopGEPs22eZfXbA-U_-Fdn9tqpeuDwM"

bot = Bot(token='8285221368:AAGeHopGEPs22eZfXbA-U_-Fdn9tqpeuDwM')
dp = Dispatcher()

users = set()
first_start_times = {}

user_names = {}
user_notes = {}

@dp.message(Command("start"))
async def send_hello(message: types.Message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    first_name = message.from_user.first_name or "Пользователь"

    if user_id not in first_start_times:
        first_start_times[user_id] = datetime.now().strftime("%d.%m.%Y %H:%M")

    if user_id not in users:
        users.add(user_id)
        await message.answer(f"Привет, {user_name}! 👋\n"
                         f"Я Бот-Переводчик. Я помогу тебе переводить тексты на другие языки!. \n\n"
                         f"Ты теперь в списке пользователей! 💾"
                         f"Используй команды:\n"
                         f"/help — помощь по боту\n"
                         f"/about — обо мне\n"
                         f"/info — информация о тебе\n"
                         f"/mood — настроение бота 🎭\n"
                         f"/menu — меню с кнопками 📋"
        )
    else:
        await message.answer(f"Снова привет, {user_name}! Рад тебя видеть 😊")

@dp.message(Command("menu"))
async def show_menu(message: types.Message):
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [
            types.InlineKeyboardButton(text="🔹 О боте", callback_data="about_bot"),
            types.InlineKeyboardButton(text="👨‍💻 Разработчик", callback_data="developer"),
        ],
        [
            types.InlineKeyboardButton(text="🌐 GitHub", url="https://github.com/Inexis667")
        ]
    ])
    await message.answer("📋 Главное меню:", reply_markup=keyboard)

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
        "— Реагирует на фразы «привет», «что делаешь», «пока» и т.д.\n"
        "— Распознаёт фото и стикеры\n"
        "— Отображает меню с кнопками 📋"
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
    await message.answer(
        "🆘 <b>Помощь по командам:</b>\n\n"
        "💬 /start — начать работу с ботом\n"
        "ℹ️ /about — информация о проекте\n"
        "👤 /info — данные о пользователе\n"
        "🎭 /mood — текущее настроение бота\n"
        "🗒 /setname &lt;имя&gt; — установить имя\n"
        "📘 /addnote &lt;заголовок&gt;; &lt;текст&gt; — добавить заметку\n"
        "📋 /notes — список заметок\n"
        "А ещё можешь написать мне фразы вроде:\n"
        "«Привет», «Как дела», «Что делаешь», «Пока»\n"
        "❓ Если напишешь вопрос (с '?'), я отреагирую особым образом 😉\n"
        "Если введёшь неизвестную команду — подскажу 😉",
        parse_mode="HTML"
    )

@dp.message(Command("about"))
async def send_about(message: types.Message):
    await message.answer(
        "📘 <b>О проекте:</b>\n\n"
        "Автор: <b>Аманшукур Алижан</b>\n"
        "Проект: <i>Учебный Бот-Переводчик на Python (Aiogram)</i>\n",
        parse_mode="HTML"
    )

@dp.message(Command("info"))
async def send_info(message: types.Message):
    user_id = message.from_user.id

    name = user_names.get(user_id, message.from_user.first_name)
    username = f"@{message.from_user.username}" if message.from_user.username else "—"

    start_time = first_start_times.get(
        user_id, datetime.now().strftime("%d.%m.%Y %H:%M")
    )

    await message.answer(
        f"👤 <b>Информация о тебе:</b>\n\n"
        f"🪪 Имя: <b>{name}</b>\n"
        f"🆔 Telegram ID: <code>{user_id}</code>\n"
        f"🕒 Первый запуск: {start_time}",
        parse_mode="HTML"
    )

@dp.message(Command("mood"))
async def send_mood(message: types.Message):
    moods = ["😊 Отличное!", "😐 Нормальное", "😴 Сонное", "🤩 Замечательное!", "🤔 Задумчивое"]
    await message.answer(f"🎭 Настроение бота: {random.choice(moods)}")

user_name = None  # Имя пользователя
notes = []  # Список заметок


@dp.message(Command("setname"))
async def set_name(message: types.Message):
    user_id = message.from_user.id
    text = message.text or ""
    args = text.split(maxsplit=1)

    if len(args) < 2 or not args[1].strip():
        await message.answer("❌ Укажи имя. Пример: /setname Алижан")
        return

    name = args[1].strip()
    user_names[user_id] = name
    await message.answer(f"✅ Имя сохранено: <b>{name}</b>", parse_mode="HTML")


@dp.message(Command("hello"))
async def send_hello(message: types.Message):
    user_id = message.from_user.id
    name = user_names.get(user_id)

    if not name:
        await message.answer("⚠️ Сначала установи имя с помощью команды /setname &lt;имя&gt;", parse_mode="HTML")
        return

    await message.answer(f"👋 Привет, {name}!")


@dp.message(Command("addnote"))
async def add_note(message: types.Message):
    user_id = message.from_user.id
    text = message.text or ""
    args = text.split(maxsplit=1)

    if len(args) < 2:
        await message.answer("❌ Укажи заметку в формате:\n/addnote Заголовок; Текст")
        return

    data = args[1].split(";", maxsplit=1)
    if len(data) < 2:
        await message.answer(
            "⚠️ Раздели заголовок и текст с помощью ';'\nПример: /addnote Покупки; Молоко, хлеб, масло")
        return

    title = data[0].strip()
    note_text = data[1].strip()

    if user_id not in user_notes:
        user_notes[user_id] = []

    user_notes[user_id].append({"title": title, "text": note_text})
    await message.answer(f"📝 Заметка добавлена:\n<b>{title}</b> — {note_text}", parse_mode="HTML")

@dp.message(Command("notes"))
async def show_notes(message: types.Message):
    user_id = message.from_user.id
    notes = user_notes.get(user_id, [])

    if not notes:
        await message.answer("📭 Список заметок пуст.")
        return

    text = "\n\n".join([f"📝 <b>{note['title']}</b> — {note['text']}" for note in notes])
    await message.answer(text, parse_mode="HTML")

@dp.message(F.photo)
async def handle_photo(message: types.Message):
    print(f"[Фото] От {message.from_user.first_name}")
    await message.answer("Классная картинка! 📸")

@dp.message(F.sticker)
async def handle_sticker(message: types.Message):
    print(f"[Стикер] От {message.from_user.first_name}")
    await message.answer("Прикольный стикер! 😎")

@dp.message(F.text)
async def echo_message(message: types.Message):
    user_text = message.text.lower().strip()

    if user_text.startswith("/"):
        await message.answer("❌ Неизвестная команда. Попробуйте /help")
        return

    if "?" in user_text:
        await message.answer("🤔 Хороший вопрос! Но я пока не знаю ответа.")
        return

    greetings = ["Привет!", "Здравствуй!", "Хэй!", "Привет-привет!"]
    how_are_you = ["Отлично!", "Нормально, спасибо 😊", "Замечательно!", "Всё супер!"]
    what_doing = ["Отвечаю на сообщения 💬", "Думаю о коде Python 🐍", "Помогаю студентам! 🎓"]
    goodbyes = ["Пока!", "До скорого!", "Было приятно пообщаться!", "Увидимся 👋"]
    if user_text in ["привет", "здравствуй", "хай", "йо"]:
        await message.answer(random.choice(greetings))
    elif user_text in ["как дела", "как ты"]:
        await message.answer(random.choice(how_are_you))
    elif user_text in ["что делаешь", "чем занят"]:
        await message.answer(random.choice(what_doing))
    elif user_text in ["пока", "до свидания", "бай"]:
        await message.answer(random.choice(goodbyes))
    else:
        await message.answer("😅 Я пока не знаю, как ответить.")

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
