from aiogram import Router, Bot
from aiogram.filters import CommandStart, Filter, Command
from aiogram.types import Message
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext

from openai import AsyncOpenAI
from config import OPEN_API_KEY

from app.database.requests import set_user, get_user


router = Router()
ADMINS = [607516284, 570575900]

# Получаем API
client = AsyncOpenAI(
    api_key=OPEN_API_KEY,
)


# Генерация ответа от chatGPT
async def generate_answer(user_message):
    chat_completion = await client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": f"{user_message}",
            }
        ],
        model="gpt-3.5-turbo",
    )
    return chat_completion.choices[0].message.content

# Кастомный фильтр для админов
class AdminProtect(Filter):
    def __init__(self):
        self.admins = ADMINS

    async def __call__(self, message: Message):
        return message.from_user.id in self.admins


# Процесс регенерации сообщений
class AntiFlood(StatesGroup):
    generating_message = State()


class Newsletter(StatesGroup):
    message = State()


# Команда /start
@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await set_user(message.from_user.id)
    await message.answer(text="Привет!")


# Реакция на админа
@router.message(AdminProtect(), Command("newsletter"))
async def admin(message: Message, state: FSMContext):
    await state.set_state(Newsletter.message)
    await message.answer("Отправьте сообщение для рассылки!")


@router.message(AdminProtect(), Newsletter.message)
async def get_admin(message: Message, state: FSMContext, bot: Bot):
    users = await get_user()
    for user in users:
        try:
            await bot.send_message(chat_id=user.tg_id, text=message.text)
        except:
            print("user banned")
    await message.answer("Рассылка завершена!")


# Ловим ошибку в боте (если пользователь вводит сообщения, не получив ответа)
@router.message(AntiFlood.generating_message)
async def anti_flood(message: Message, state: FSMContext):
    await message.answer("Вы ещё не получили ответа! Если это ошибка, перезапустите бота /start.")


# Ответ на все сообщения
@router.message()
async def all_answer(message: Message, state: FSMContext):
    await state.set_state(AntiFlood.generating_message)
    answer = await generate_answer(message.text)
    await message.answer(f"{answer}")
    await state.clear()
