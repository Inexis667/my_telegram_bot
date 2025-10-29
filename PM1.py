from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.state import StatesGroup, State
from aiogram.fsm.context import FSMContext
import asyncio
import logging

BOT_TOKEN = "8285221368:AAGeHopGEPs22eZfXbA-U_-Fdn9tqpeuDwM"

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

logging.basicConfig(level=logging.INFO)

class FoodForm(StatesGroup):
    name = State()
    dish = State()
    rating = State()


@dp.message(Command("food"))
async def start_food(message: types.Message, state: FSMContext):
    await message.answer("Привет! Как тебя зовут?")
    await state.set_state(FoodForm.name)


@dp.message(FoodForm.name)
async def get_name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)
    await message.answer("Какое твоё любимое блюдо?")
    await state.set_state(FoodForm.dish)


@dp.message(FoodForm.dish)
async def get_dish(message: types.Message, state: FSMContext):
    await state.update_data(dish=message.text)
    await message.answer("Оцени его от 1 до 5 ⭐️")
    await state.set_state(FoodForm.rating)


@dp.message(FoodForm.rating)
async def get_rating(message: types.Message, state: FSMContext):
    data = await state.get_data()
    name = data["name"]
    dish = data["dish"]
    rating = message.text

    await message.answer(
        f"🍽 Имя: {name}\nЛюбимое блюдо: {dish}\nОценка: {rating}⭐️"
    )

    await state.clear()


@dp.message(Command("cancel"))
async def cancel(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("Действие отменено. Вы можете начать заново командой /food.")

async def main():
    print("Бот запущен...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())