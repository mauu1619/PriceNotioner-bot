from aiogram.types import KeyboardButton, ReplyKeyboardMarkup


def get_main_menu() -> ReplyKeyboardMarkup:
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="➕ Добавить товар"),
                KeyboardButton(text="📦 Мои товары"),
            ],
            [
                KeyboardButton(text="💎 Мой профиль"),
                KeyboardButton(text="⭐️ Баланс Stars"),
            ],
        ],
        resize_keyboard=True,
    )
    return keyboard
