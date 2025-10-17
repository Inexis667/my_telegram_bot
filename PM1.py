import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types.error_event import ErrorEvent
import asyncio
import math

BOT_TOKEN = "8285221368:AAGeHopGEPs22eZfXbA-U_-Fdn9tqpeuDwM"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("divide"))
async def divide(message: types.Message):
    try:
        parts = message.text.split()
        if len(parts) != 3:
            await message.answer("⚠️ Формат команды: /divide <число1> <число2>")
            return

        _, a, b = parts
        a = float(a)
        b = float(b)

        if b == 0:
            await message.answer("❌ Деление на ноль невозможно")
            return

        await message.answer(f"✅ Результат: {a / b}")

    except ValueError:
        await message.answer("⚠️ Введите два числа, например: /divide 10 2")
    except Exception:
        await message.answer("⚠️ Что-то пошло не так, попробуй позже")

@dp.message(Command("calc"))
async def calc(message: types.Message):
    try:
        # Получаем выражение после команды
        expr = message.text.replace("/calc", "").strip()

        if not expr:
            await message.answer("⚠️ Укажи выражение, например: /calc 2 + 3 * 4")
            return

        allowed_names = {k: v for k, v in math.__dict__.items() if not k.startswith("__")}
        result = eval(expr, {"__builtins__": {}}, allowed_names)

        await message.answer(f"✅ Результат: {result}")

    except ZeroDivisionError:
        await message.answer("❌ Деление на ноль невозможно")
    except Exception:
        await message.answer("Неверное выражение!")


@dp.errors()
async def global_error_handler(event: ErrorEvent):
    print("Ошибка:", event.exception)
    try:
        if event.update and event.update.message:
            await event.update.message.answer("⚠️ Внутренняя ошибка! Попробуй позже.")
    except Exception:
        pass

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())