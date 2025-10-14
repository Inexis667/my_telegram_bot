
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram import F
import asyncio

BOT_TOKEN = "8285221368:AAGeHopGEPs22eZfXbA-U_-Fdn9tqpeuDwM"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(Command("calc"))
async def calc(message: types.Message):
    try:
        parts = message.text.split()

        if len(parts) != 4:
            await message.answer("⚠️ Формат: /calc число операция число\nПример: /calc 10 + 5")
            return

        _, num1, op, num2 = parts

        num1 = float(num1)
        num2 = float(num2)

        if op == "+":
            result = num1 + num2
        elif op == "-":
            result = num1 - num2
        elif op == "*":
            result = num1 * num2
        elif op == "/":
            if num2 == 0:
                await message.answer("❌ Ошибка: деление на 0 запрещено.")
                return
            result = num1 / num2
        else:
            await message.answer("⚙️ Поддерживаются только операции: +, -, *, /")
            return

        await message.answer(f"✅ Результат: {result}")

    except ValueError:
        await message.answer("⚠️ Ошибка: введите корректные числа.")
    except Exception as e:
        await message.answer(f"⚙️ Произошла ошибка: {type(e).__name__}")

@dp.errors()
async def global_error_handler(update, exception):
    try:
        if isinstance(exception, TelegramBadRequest):
            await update.message.answer("⚠️ Telegram не принял запрос (возможно, слишком длинный текст).")
        else:
            await update.message.answer("⚙️ Что-то пошло не так... Попробуй ещё раз.")
    except Exception:
        # Если даже отправка сообщения вызвала ошибку — просто игнорируем
        pass


async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())