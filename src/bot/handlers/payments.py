from datetime import datetime, timedelta

from aiogram import F, Router
from aiogram.types import CallbackQuery, LabeledPrice, Message, PreCheckoutQuery
from loguru import logger
from sqlmodel import select

from src.bot.keyboards.inline import get_pro_subscription_keyboard
from src.db.models.models import Payment, Plan, User

router = Router(name="payments_commands")


@router.message(F.text == "💎 Мой профиль")
async def cmd_my_subscriptions(message: Message, db_user: User, db_session):
    logger.info(f"User {db_user.id} opened 'Мой профиль'.")
    stmt_plan = select(Plan).where(Plan.id == db_user.plan_id)
    result_plan = await db_session.execute(stmt_plan)
    current_plan = result_plan.scalar_one()

    text = (
        f"👤 <b>Твой текущий профиль</b>\n\n"
        f"🏷 Тариф: <b>{current_plan.name}</b>\n"
        f"📦 Лимит товаров: <b>{current_plan.max_products}</b>\n"
        f"⏱ Интервал проверки: каждые <b>{current_plan.check_interval_minutes} мин.</b>\n\n"
    )

    if current_plan.name == "Pro" and db_user.subscription_expires_at:
        text += f"📅 Подписка активна до: <b>{db_user.subscription_expires_at.strftime('%Y-%m-%d %H:%M')}</b>"
        await message.answer(text)
        return

    # If Free, offer Pro
    stmt_pro = select(Plan).where(Plan.name == "Pro")
    result_pro = await db_session.execute(stmt_pro)
    pro_plan = result_pro.scalar_one_or_none()

    if pro_plan:
        text += (
            f"🚀 <b>Переходи на PRO!</b>\n\n"
            f"С ним ты сможешь добавить до <b>{pro_plan.max_products} товаров</b>, "
            f"а проверять цены я буду намного чаще — раз в <b>{pro_plan.check_interval_minutes} минут</b>!\n\n"
            f"💎 Стоимость: <b>{pro_plan.stars_price} Telegram Stars</b> на 30 дней."
        )
        await message.answer(
            text, reply_markup=get_pro_subscription_keyboard(pro_plan.stars_price)
        )
    else:
        await message.answer(text)


@router.message(F.text == "⭐️ Баланс Stars")
async def cmd_stars_balance(message: Message):
    logger.info(f"User {message.chat.id} requested 'Баланс Stars'.")
    await message.answer(
        "⭐️ <b>Твой баланс Telegram Stars</b>\n\n"
        "Telegram Stars — это глобальная валюта мессенджера, она не хранится отдельно в каждом боте. "
        "Свой точный баланс ты можешь увидеть:\n\n"
        "📱 <b>На Android/iOS:</b> Настройки -> Мои Stars\n"
        "🖥 <b>В десктопе:</b> Настройки -> Telegram Stars\n\n"
        "💳 Пополнить баланс можно там же или прямо во время покупки PRO-тарифа в нашем боте!"
    )


@router.callback_query(F.data == "buy_pro")
async def process_buy_pro_callback(callback: CallbackQuery, db_user: User, db_session):
    logger.info(f"User {db_user.id} clicked 'buy_pro' button.")
    # Fetch pro plan price
    stmt_pro = select(Plan).where(Plan.name == "Pro")
    result_pro = await db_session.execute(stmt_pro)
    pro_plan = result_pro.scalar_one()

    prices = [LabeledPrice(label="PRO Тариф (30 дней)", amount=pro_plan.stars_price)]

    if callback.message:
        # Provide an empty provider token for Telegram Stars
        await callback.message.answer_invoice(
            title="PRO Тариф 🚀",
            description=f"Подписка на PRO тариф на 30 дней. Лимит: {pro_plan.max_products} товаров.",
            payload="pro_subscription_payload",
            provider_token="",  # Important: empty string for Telegram Stars
            currency="XTR",
            prices=prices,
        )
    await callback.answer()


@router.pre_checkout_query()
async def process_pre_checkout_query(pre_checkout_query: PreCheckoutQuery):
    logger.info(
        f"Processing pre_checkout_query for user {pre_checkout_query.from_user.id}."
    )
    # Here you can validate if the item is still available or the user is eligible.
    await pre_checkout_query.answer(ok=True)


@router.message(F.successful_payment)
async def process_successful_payment(message: Message, db_user: User, db_session):
    successful_payment = message.successful_payment

    if not successful_payment:
        return

    logger.info(
        f"Received successful payment from user {db_user.id}: {successful_payment.total_amount} XTR"
    )

    # Fetch pro plan
    stmt_pro = select(Plan).where(Plan.name == "Pro")
    result_pro = await db_session.execute(stmt_pro)
    pro_plan = result_pro.scalar_one()

    # Create Payment record
    new_payment = Payment(
        user_id=db_user.id,
        telegram_payment_charge_id=successful_payment.telegram_payment_charge_id,
        stars_amount=successful_payment.total_amount,
        status="success",
    )
    db_session.add(new_payment)

    # Update User plan
    db_user.plan_id = int(pro_plan.id) if pro_plan.id is not None else 2

    # Extend subscription
    now = datetime.utcnow()
    if db_user.subscription_expires_at and db_user.subscription_expires_at > now:
        db_user.subscription_expires_at += timedelta(days=30)
    else:
        db_user.subscription_expires_at = now + timedelta(days=30)

    await db_session.commit()
    logger.info(f"User {db_user.id} successfully upgraded to {pro_plan.name} plan.")

    await message.answer(
        "🎉 <b>Оплата прошла успешно! Спасибо за поддержку!</b> 💖\n\n"
        f"Твой тариф обновлен до <b>{pro_plan.name}</b> 🚀\n"
        f"Теперь ты можешь добавить до {pro_plan.max_products} товаров, "
        f"и я буду следить за ними каждые {pro_plan.check_interval_minutes} минут! Приятных покупок! 🛍"
    )
