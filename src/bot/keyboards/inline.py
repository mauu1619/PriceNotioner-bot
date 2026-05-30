from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup


def get_pro_subscription_keyboard(stars_price: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text=f"Купить PRO-тариф ⭐️ ({stars_price} Stars)",
                    callback_data="buy_pro",
                )
            ]
        ]
    )
