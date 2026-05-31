import asyncio
from datetime import datetime, timedelta

from aiogram import Bot, F, Router
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import func, select

from src.bot.keyboards.admin import (
    get_admin_main_menu,
    get_broadcast_confirm_keyboard,
    get_user_manage_menu,
)
from src.bot.states.admin import AdminStates
from src.core.config import settings
from src.db.models.models import Payment, Plan, Product, User

router = Router(name="admin_commands")


# Simple filter for admin
async def admin_filter(event: Message | CallbackQuery) -> bool:
    if event.from_user is None:
        return False
    return event.from_user.id in settings.ADMIN_IDS


@router.message(Command("admin"), admin_filter)
async def cmd_admin(message: Message, state: FSMContext):
    await state.clear()
    await message.answer(
        "👋 Добро пожаловать в админ-панель!", reply_markup=get_admin_main_menu()
    )


@router.callback_query(F.data == "admin_main_menu", admin_filter)
async def cb_admin_main_menu(callback: CallbackQuery):
    if callback.message and isinstance(callback.message, Message):
        await callback.message.edit_text(
            "👋 Добро пожаловать в админ-панель!", reply_markup=get_admin_main_menu()
        )
    await callback.answer()


@router.callback_query(F.data == "admin_stats", admin_filter)
async def cb_admin_stats(callback: CallbackQuery, db_session: AsyncSession):
    # Total users
    stmt_users = select(func.count()).select_from(User)
    users_count = (await db_session.execute(stmt_users)).scalar() or 0

    # Active products
    stmt_products = select(func.count()).select_from(Product)
    products_count = (await db_session.execute(stmt_products)).scalar() or 0

    # Total payments
    stmt_payments = select(func.count()).select_from(Payment)
    payments_count = (await db_session.execute(stmt_payments)).scalar() or 0

    # Stars amount
    stmt_stars = select(func.sum(Payment.stars_amount))
    stars_sum_result = await db_session.execute(stmt_stars)
    stars_sum = stars_sum_result.scalar() or 0

    stats_text = (
        f"📊 <b>Статистика бота:</b>\n\n"
        f"👤 Всего пользователей: <b>{users_count}</b>\n"
        f"📦 Активных товаров: <b>{products_count}</b>\n"
        f"💳 Всего оплат: <b>{payments_count}</b>\n"
        f"⭐️ Всего звёзд: <b>{stars_sum}</b>"
    )

    if callback.message and isinstance(callback.message, Message):
        await callback.message.edit_text(stats_text, reply_markup=get_admin_main_menu())
    await callback.answer()


@router.callback_query(F.data == "admin_broadcast", admin_filter)
async def cb_admin_broadcast(callback: CallbackQuery, state: FSMContext):
    if callback.message and isinstance(callback.message, Message):
        await callback.message.answer(
            "📝 Введи сообщение для рассылки всем пользователям:"
        )
        await state.set_state(AdminStates.waiting_for_broadcast_message)
    await callback.answer()


@router.message(AdminStates.waiting_for_broadcast_message, admin_filter)
async def process_broadcast_message(message: Message, state: FSMContext):
    await state.update_data(broadcast_text=message.text)
    await message.answer(
        f"📣 <b>Предпросмотр сообщения:</b>\n\n{message.text}\n\n"
        "Вы уверены, что хотите отправить это всем пользователям?",
        reply_markup=get_broadcast_confirm_keyboard(),
    )


@router.callback_query(F.data == "admin_broadcast_confirm", admin_filter)
async def cb_broadcast_confirm(
    callback: CallbackQuery, state: FSMContext, db_session: AsyncSession, bot: Bot
):
    data = await state.get_data()
    text = data.get("broadcast_text")

    if not text:
        if callback.message and isinstance(callback.message, Message):
            await callback.message.answer("❌ Ошибка: сообщение не найдено.")
        await callback.answer()
        return

    stmt = select(User.id)
    result = await db_session.execute(stmt)
    user_ids = result.scalars().all()

    if callback.message and isinstance(callback.message, Message):
        await callback.message.edit_text(
            f"🚀 Начинаю рассылку на {len(user_ids)} пользователей..."
        )

    success = 0
    failed = 0

    for user_id in user_ids:
        try:
            await bot.send_message(user_id, text)
            success += 1
            await asyncio.sleep(0.05)  # Rate limiting
        except Exception as e:
            logger.error(f"Failed to send broadcast to {user_id}: {e}")
            failed += 1

    if callback.message and isinstance(callback.message, Message):
        await callback.message.answer(
            f"✅ Рассылка завершена!\nУспешно: {success}\nОшибок: {failed}"
        )
    await state.clear()
    await callback.answer()


@router.callback_query(F.data == "admin_broadcast_cancel", admin_filter)
async def cb_broadcast_cancel(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    if callback.message and isinstance(callback.message, Message):
        await callback.message.edit_text(
            "❌ Рассылка отменена.", reply_markup=get_admin_main_menu()
        )
    await callback.answer()


@router.callback_query(F.data == "admin_user_search", admin_filter)
async def cb_user_search(callback: CallbackQuery, state: FSMContext):
    if callback.message and isinstance(callback.message, Message):
        await callback.message.answer("🔍 Введи ID пользователя или его username:")
        await state.set_state(AdminStates.waiting_for_user_search)
    await callback.answer()


@router.message(AdminStates.waiting_for_user_search, admin_filter)
async def process_user_search(
    message: Message, state: FSMContext, db_session: AsyncSession
):
    search_query = message.text

    if not search_query:
        return

    if search_query.isdigit():
        stmt = select(User).where(User.id == int(search_query))
    else:
        username = search_query.replace("@", "")
        stmt = select(User).where(User.username == username)

    result = await db_session.execute(stmt)
    user = result.scalar_one_or_none()

    if not user:
        await message.answer("❌ Пользователь не найден.")
        return

    # Get user plan
    plan_stmt = select(Plan).where(Plan.id == user.plan_id)
    plan_result = await db_session.execute(plan_stmt)
    plan = plan_result.scalar_one()

    user_info = (
        f"👤 <b>Пользователь:</b>\n"
        f"ID: <code>{user.id}</code>\n"
        f"Username: @{user.username if user.username else 'нет'}\n"
        f"Тариф: <b>{plan.name}</b>\n"
        f"Дата регистрации: {user.created_at.strftime('%d.%m.%Y %H:%M')}\n"
    )

    await message.answer(user_info, reply_markup=get_user_manage_menu(user.id))
    await state.clear()


@router.callback_query(F.data.startswith("admin_give_pro_"), admin_filter)
async def cb_give_pro(callback: CallbackQuery, db_session: AsyncSession, bot: Bot):
    # admin_give_pro_{user_id}_{days/forever}
    if not callback.data:
        await callback.answer()
        return

    parts = callback.data.split("_")
    user_id = int(parts[3])
    duration = parts[4]

    # Get Pro plan
    plan_stmt = select(Plan).where(Plan.name == "Pro")
    plan_result = await db_session.execute(plan_stmt)
    pro_plan = plan_result.scalar_one()

    if pro_plan.id is None:
        await callback.answer("❌ Ошибка: тариф Pro не найден в БД.")
        return

    stmt = select(User).where(User.id == user_id)
    user_result = await db_session.execute(stmt)
    user = user_result.scalar_one()

    user.plan_id = pro_plan.id
    if duration == "forever":
        user.subscription_expires_at = None
        duration_text = "навсегда ✨"
    else:
        # 30 days
        user.subscription_expires_at = datetime.utcnow() + timedelta(days=30)
        duration_text = "на 30 дней 🚀"

    await db_session.commit()

    # Send notification to user
    try:
        notification_text = (
            f"🎉 <b>Поздравляем!</b>\n\n"
            f"Администратор активировал тебе тариф <b>Pro</b> {duration_text}!\n\n"
            f"🚀 Теперь тебе доступно:\n"
            f"• До <b>{pro_plan.max_products}</b> товаров для отслеживания\n"
            f"• Проверка цен каждые <b>{pro_plan.check_interval_minutes}</b> минут\n\n"
            f"Приятного использования! 🛍"
        )
        await bot.send_message(user_id, notification_text)
    except Exception as e:
        logger.error(f"Failed to send gift notification to {user_id}: {e}")

    if callback.message and isinstance(callback.message, Message):
        await callback.message.answer(
            f"✅ Пользователю {user_id} выдан тариф Pro ({duration}) и отправлено уведомление."
        )
    await callback.answer()


@router.callback_query(F.data.startswith("admin_view_products_"), admin_filter)
async def cb_view_products(callback: CallbackQuery, db_session: AsyncSession):
    if not callback.data:
        await callback.answer()
        return

    user_id = int(callback.data.split("_")[3])

    stmt = select(Product).where(Product.user_id == user_id)
    result = await db_session.execute(stmt)
    products = result.scalars().all()

    if not products:
        if callback.message and isinstance(callback.message, Message):
            await callback.message.answer("📦 У пользователя нет активных товаров.")
        await callback.answer()
        return

    text = f"📦 <b>Товары пользователя {user_id}:</b>\n\n"
    for i, p in enumerate(products, 1):
        text += (
            f"{i}. {p.title}\nЦена: {p.current_price} ₽ -> Цель: {p.target_price} ₽\n"
        )

    if callback.message and isinstance(callback.message, Message):
        await callback.message.answer(text)
    await callback.answer()
