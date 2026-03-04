from aiogram.types import ReplyKeyboardMarkup, KeyboardButton

main_keyboard = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📅 День"), KeyboardButton(text="📊 Неделя"), KeyboardButton(text="📊 Месяц")],
    ],
    resize_keyboard=True,
    input_field_placeholder="Напиши расход или отправь голосовое...",
)
