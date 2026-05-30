from aiogram.types import InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder

from src.db.models.models import Product


def get_products_keyboard(products: list[Product]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for p in products:
        fav_icon = "⭐ " if p.is_favorite else ""
        builder.button(
            text=f"{fav_icon}{p.title[:25]}", callback_data=f"prod_details_{p.id}"
        )
    builder.adjust(1)
    return builder.as_markup()


def get_product_options_keyboard(product: Product) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()

    fav_text = "❌ Удалить из Избранного" if product.is_favorite else "⭐ В Избранное"
    builder.button(text=fav_text, callback_data=f"toggle_fav_{product.id}")

    builder.button(
        text="📉 Изменить желаемую цену", callback_data=f"set_target_{product.id}"
    )
    builder.button(
        text="🎯 Изменить порог (руб)", callback_data=f"set_threshold_{product.id}"
    )

    builder.button(text="🗑 Удалить товар", callback_data=f"del_prod_{product.id}")
    builder.button(text="🔙 Назад к списку", callback_data="back_to_products")

    builder.adjust(1)
    return builder.as_markup()
