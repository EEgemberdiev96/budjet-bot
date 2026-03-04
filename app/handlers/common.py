from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import Message
from app.db.queries import ensure_user, get_user_name, set_user_name
from app.keyboards.main import main_keyboard

router = Router()


class Registration(StatesGroup):
    waiting_for_name = State()


@router.message(CommandStart())
async def cmd_start(message: Message, state: FSMContext):
    await ensure_user(message.from_user.id, message.from_user.username)
    name = await get_user_name(message.from_user.id)

    if name:
        await message.answer(
            f"Привет, {name}! 👋\n\n"
            "Просто напиши расход или отправь голосовое.\n"
            "Например: «купил хлеб 50 сом»",
            reply_markup=main_keyboard,
        )
    else:
        await message.answer("Привет! Как тебя зовут?")
        await state.set_state(Registration.waiting_for_name)


@router.message(Registration.waiting_for_name)
async def handle_name(message: Message, state: FSMContext):
    name = message.text.strip()
    await set_user_name(message.from_user.id, name)
    await state.clear()
    await message.answer(
        f"Приятно познакомиться, {name}! 🎉\n\n"
        "Просто напиши расход или отправь голосовое.\n"
        "Например: «купил хлеб 50 сом»",
        reply_markup=main_keyboard,
    )
