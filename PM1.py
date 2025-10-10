from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram import F
import asyncio

BOT_TOKEN = "8285221368:AAGeHopGEPs22eZfXbA-U_-Fdn9tqpeuDwM"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("start"))
async def send_hello(message: types.Message):
    user_name = message.from_user.first_name
    await message.answer(f"Привет, {user_name}!.\nЯ Бот-Переводчик, я помогу тебе переводить текст на другом языке!")

@dp.message(Command("hello"))
async def send_hello(message: types.Message):
    await message.answer("Привет! Я твой первый Telegram-бот!")

@dp.message(Command("help"))
async def send_help(message: types.Message):
    await message.answer('Доступные команды:\n/start - начать\n/help — помощь\n/hello — поздороваться\n/about — обо мне.')

@dp.message(Command("about"))
async def send_about(message: types.Message):
    await message.answer('Я создан для перевода текста с других языков. Обращайся в любой момент! ')

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())