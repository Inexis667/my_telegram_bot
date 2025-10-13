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

@dp.message(Command("start"))
async def send_hello(message: types.Message):
    user_id = message.from_user.id
    user_name = message.from_user.first_name

    if user_id not in first_start_times:
        first_start_times[user_id] = datetime.now().strftime("%d.%m.%Y %H:%M")

    if user_id not in users:
        users.add(user_id)
        await message.answer(f"Привет, {user_name}! 👋\n"
                         f"Я Эхо-Бот и Бот-Переводчик. Я помогу тебе переводить тексты на другие языки, а также повторю твое сообщение!. \n\n"
                         f"Ты теперь в списке пользователей! 💾"
                         f"Используй команды:\n"
                         f"/help — помощь по боту\n"
                         f"/about — обо мне\n"
                         f"/info — информация о тебе\n"
                         f"/mood — настроение бота 🎭\n\n"
        )
    else:
        await message.answer(f"Снова привет, {user_name}! Рад тебя видеть 😊")

@dp.message(Command("hello"))
async def send_hello(message: types.Message):
    await message.answer("Привет! Я твой первый Telegram-бот!")

@dp.message(Command("help"))
async def send_help(message: types.Message):
    await message.answer(
        "🆘 <b>Помощь по командам:</b>\n\n"
        "💬 /start — начать работу с ботом\n"
        "ℹ️ /about — информация о проекте\n"
        "👤 /info — данные о пользователе\n"
        "🎭 /mood — текущее настроение бота\n\n"
        "А ещё можешь написать мне фразы вроде:\n"
        "«Привет», «Как дела», «Что делаешь», «Пока»\n\n"
        "❓ Просто напиши сообщение — я повторю его!\n\n"
        "❓ Если напишешь вопрос (с '?'), я отреагирую особым образом 😉\n"
        "Если введёшь неизвестную команду — подскажу 😉",
        parse_mode="HTML"
    )

@dp.message(Command("about"))
async def send_about(message: types.Message):
    await message.answer(
        "📘 <b>О проекте:</b>\n\n"
        "Автор: <b>Аманшукур Алижан</b>\n"
        "Проект: <i>Учебный Эхо-Бот и Бот-Переводчик на Python (Aiogram)</i>\n\n"
        "🎯 Функции:\n"
        "— Отвечает на команды /start, /help, /about, /info\n"
        "— Переводит текст на любой другой язык\n"
        "— Повторяет текст пользователя\n"
        "— Распознаёт фото и стикеры\n"
        "— Реагирует на фразы «привет», «как дела», «что делаешь», «пока»\n"
        "— Понимает вопросы\n"
        "— Отвечает случайными вариантами\n"
        "— Может показать настроение 🥳"
        "— Проверяет тип текста (число, текст, смешанное)\n",
        parse_mode="HTML"
    )

@dp.message(Command("info"))
async def send_info(message: types.Message):
    user = message.from_user
    start_time = first_start_times.get(user.id, datetime.now().strftime("%d.%m.%Y %H:%M"))
    await message.answer(
        f"👤 <b>Информация о тебе:</b>\n\n"
        f"🪪 Имя: <b>{user.full_name}</b>\n"
        f"🆔 Telegram ID: <code>{user.id}</code>\n"
        f"🕒 Первый запуск: {start_time}",
        parse_mode="HTML"
    )

@dp.message(Command("mood"))
async def send_mood(message: types.Message):
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

    #print(f"[Текст от {message.from_user.first_name}]: {text}")
    #if text.isdigit():
    #    msg_type = "Это число!"
    #elif text.isalpha():
    #    msg_type = "Это текст!"
    #else:
    #    msg_type = "Смешанный ввод!"

    #await message.answer(f"Ты сказал: {text}\n{msg_type}")

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
