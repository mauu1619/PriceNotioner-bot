from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.keyboard import InlineKeyboardBuilder


def get_admin_main_menu() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(text="📊 Статистика", callback_data="admin_stats"),
        InlineKeyboardButton(text="📢 Рассылка", callback_data="admin_broadcast"),
    )
    builder.row(
        InlineKeyboardButton(
            text="🔍 Поиск пользователя", callback_data="admin_user_search"
        ),
    )
    return builder.as_markup()


def get_user_manage_menu(user_id: int) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="🚀 Дать PRO (30 дней)", callback_data=f"admin_give_pro_{user_id}_30"
        ),
        InlineKeyboardButton(
            text="💎 Дать PRO (навсегда)",
            callback_data=f"admin_give_pro_{user_id}_forever",
        ),
    )
    builder.row(
        InlineKeyboardButton(
            text="📦 Просмотреть товары", callback_data=f"admin_view_products_{user_id}"
        )
    )
    builder.row(InlineKeyboardButton(text="⬅️ Назад", callback_data="admin_main_menu"))
    return builder.as_markup()


def get_broadcast_confirm_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    builder.row(
        InlineKeyboardButton(
            text="✅ Отправить", callback_data="admin_broadcast_confirm"
        ),
        InlineKeyboardButton(text="❌ Отмена", callback_data="admin_broadcast_cancel"),
    )
    return builder.as_markup()
