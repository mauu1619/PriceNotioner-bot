from decimal import Decimal, InvalidOperation

from aiogram import F, Router
from aiogram.fsm.context import FSMContext
from aiogram.types import CallbackQuery, Message
from loguru import logger
from sqlmodel import select

from src.bot.keyboards.main_menu import get_main_menu
from src.bot.keyboards.products import (
    get_product_options_keyboard,
    get_products_keyboard,
)
from src.bot.states.product import AddProductState, EditProductState
from src.db.models.models import Plan, Product, User
from src.parsers.wildberries import get_wb_product

router = Router(name="product_commands")


@router.message(F.text == "➕ Добавить товар")
async def cmd_add_product(
    message: Message, state: FSMContext, db_user: User, db_session
):
    logger.info(f"User {db_user.id} clicked 'Добавить товар'.")
    # Check if user has reached plan limit
    stmt = select(Plan).where(Plan.id == db_user.plan_id)
    plan_result = await db_session.execute(stmt)
    plan = plan_result.scalar_one()

    stmt_products = select(Product).where(Product.user_id == db_user.id)
    products_result = await db_session.execute(stmt_products)
    products_count = len(products_result.scalars().all())

    if products_count >= plan.max_products:
        logger.warning(
            f"User {db_user.id} reached plan limit ({products_count}/{plan.max_products})."
        )
        await message.answer(
            f"😔 <b>Упс!</b> Ты достиг лимита подписок ({plan.max_products}) для тарифа <b>{plan.name}</b>.\n\n"
            "⭐️ Чтобы добавить больше товаров, пожалуйста, перейди на PRO-тариф или удали старые подписки."
        )
        return

    await message.answer(
        "🔗 <b>Отправь мне ссылку на товар</b> с Wildberries или просто его артикул (например: <code>12345678</code>) 👇",
        reply_markup=get_main_menu(),  # Keep menu or give a cancel button
    )
    await state.set_state(AddProductState.waiting_for_url)


@router.message(AddProductState.waiting_for_url)
async def process_product_url(message: Message, state: FSMContext):
    url_or_article = message.text
    if not url_or_article:
        return

    await message.answer("⏳ Проверяю товар, дай мне секундочку...")
    logger.info(f"User {message.chat.id} submitted url/article: {url_or_article}")

    parsed_data = await get_wb_product(url_or_article)
    if not parsed_data:
        logger.warning(
            f"Failed to parse url/article {url_or_article} for user {message.chat.id}."
        )
        await message.answer(
            "❌ <b>Ой, не удалось найти товар.</b> Убедись, что ссылка или артикул верны, и товар есть в наличии на сайте.\n"
            "🔄 Попробуй отправить еще раз!"
        )
        return

    title, current_price, clean_url = parsed_data

    await state.update_data(
        title=title, current_price=str(current_price), url=clean_url
    )

    await message.answer(
        f"✅ <b>Товар успешно найден!</b>\n\n"
        f"📦 Название: <b>{title}</b>\n"
        f"💸 Текущая цена: <b>{current_price:f} ₽</b>\n\n"
        f"🎯 <b>Какую желаемую цену ты хочешь отслеживать?</b> Напиши число (например, <code>{int(current_price) - 100}</code>)."
    )
    await state.set_state(AddProductState.waiting_for_target_price)


@router.message(AddProductState.waiting_for_target_price)
async def process_target_price(
    message: Message, state: FSMContext, db_user: User, db_session
):
    try:
        if not message.text:
            raise ValueError
        target_price = Decimal(message.text.replace(",", "."))
        if target_price <= 0:
            raise ValueError
    except (ValueError, InvalidOperation):
        logger.debug(f"User {db_user.id} provided invalid target price: {message.text}")
        await message.answer(
            "⚠️ Пожалуйста, введи корректную цену (целое число больше нуля)."
        )
        return

    data = await state.get_data()
    title = data["title"]
    current_price = Decimal(data["current_price"])
    url = data["url"]

    # Check if this product is already tracked by this user
    stmt = select(Product).where(Product.user_id == db_user.id, Product.url == url)
    result = await db_session.execute(stmt)
    existing_product = result.scalar_one_or_none()

    if existing_product:
        existing_product.target_price = target_price
        existing_product.current_price = current_price
        existing_product.last_notified_price = current_price
        await db_session.commit()
        logger.info(
            f"User {db_user.id} updated target price for product {existing_product.id} to {target_price:f}"
        )
        await message.answer(
            f"🔄 Этот товар уже есть в твоем списке! Желаемая цена обновлена до <b>{target_price:f} ₽</b> 🎯"
        )
    else:
        new_product = Product(
            user_id=db_user.id,
            url=url,
            title=title,
            current_price=current_price,
            target_price=target_price,
            last_notified_price=current_price,
        )
        db_session.add(new_product)
        await db_session.commit()
        logger.info(
            f"User {db_user.id} added new product: {title} (Target: {target_price:f})"
        )
        await message.answer(
            f"🎉 <b>Товар успешно добавлен!</b>\n\n"
            f"📦 <b>{title}</b>\n"
            f"💸 Текущая цена: {current_price:f} ₽\n"
            f"🎯 Желаемая цена: <b>{target_price:f} ₽</b>\n\n"
            f"🤫 Я шепну тебе, как только цена опустится до этого уровня!"
        )

    await state.clear()


@router.message(F.text == "📦 Мои товары")
async def cmd_my_products(message: Message, db_user: User, db_session):
    logger.info(f"User {db_user.id} requested their product list.")
    await show_products_list(message, db_user, db_session)


async def show_products_list(
    message: Message | CallbackQuery, db_user: User, db_session
):
    stmt = select(Product).where(Product.user_id == db_user.id)
    result = await db_session.execute(stmt)
    products = list(result.scalars().all())

    if not products:
        text = "У тебя пока нет отслеживаемых товаров 🏜.\nНажми <b>➕ Добавить товар</b>, чтобы начать!"
        if isinstance(message, Message):
            await message.answer(text)
        elif isinstance(message, CallbackQuery) and isinstance(
            message.message, Message
        ):
            await message.message.edit_text(text)
        return

    text = "📦 <b>Твои отслеживаемые товары:</b>\n\n"
    text += "<i>Выбери товар, чтобы изменить его настройки или удалить:</i>"

    if isinstance(message, Message):
        await message.answer(
            text,
            reply_markup=get_products_keyboard(products),
        )
    elif isinstance(message, CallbackQuery) and isinstance(message.message, Message):
        await message.message.edit_text(
            text,
            reply_markup=get_products_keyboard(products),
        )


@router.callback_query(F.data == "back_to_products")
async def process_back_to_products(callback: CallbackQuery, db_user: User, db_session):
    await show_products_list(callback, db_user, db_session)
    await callback.answer()


@router.callback_query(F.data.startswith("prod_details_"))
async def process_product_details(callback: CallbackQuery, db_user: User, db_session):
    if not callback.data or not callback.message:
        return

    product_id = int(callback.data.split("_")[-1])
    stmt = select(Product).where(
        Product.id == product_id, Product.user_id == db_user.id
    )
    result = await db_session.execute(stmt)
    product = result.scalar_one_or_none()

    if not product:
        await callback.answer("Товар не найден.", show_alert=True)
        return

    fav_status = "⭐ Да" if product.is_favorite else "Нет"
    text = (
        f"📦 <b>Детали товара:</b>\n\n"
        f"Название: <a href='{product.url}'>{product.title}</a>\n"
        f"Текущая цена: <b>{product.current_price:f} ₽</b>\n"
        f"Желаемая цена: <b>{product.target_price:f} ₽</b>\n"
        f"Порог уведомления: <b>{product.threshold:f} ₽</b>\n"
        f"Избранный: <b>{fav_status}</b>\n\n"
        f"<i>В 'Избранном' я сообщаю о любых изменениях выше порога.\n"
        f"В обычном режиме — только когда цена ниже желаемой.</i>"
    )

    if isinstance(callback.message, Message):
        await callback.message.edit_text(
            text,
            reply_markup=get_product_options_keyboard(product),
            disable_web_page_preview=True,
        )
    await callback.answer()


@router.callback_query(F.data.startswith("toggle_fav_"))
async def process_toggle_favorite(callback: CallbackQuery, db_user: User, db_session):
    if not callback.data:
        return

    product_id = int(callback.data.split("_")[-1])
    stmt = select(Product).where(
        Product.id == product_id, Product.user_id == db_user.id
    )
    result = await db_session.execute(stmt)
    product = result.scalar_one_or_none()

    if product:
        product.is_favorite = not product.is_favorite
        await db_session.commit()
        logger.info(
            f"User {db_user.id} toggled favorite for product {product_id} to {product.is_favorite}"
        )
        await process_product_details(callback, db_user, db_session)
    else:
        await callback.answer("Товар не найден.", show_alert=True)


@router.callback_query(F.data.startswith("del_prod_"))
async def process_delete_product(callback: CallbackQuery, db_user: User, db_session):
    if not callback.data:
        return

    product_id = int(callback.data.split("_")[-1])
    stmt = select(Product).where(
        Product.id == product_id, Product.user_id == db_user.id
    )
    result = await db_session.execute(stmt)
    product = result.scalar_one_or_none()

    if product:
        await db_session.delete(product)
        await db_session.commit()
        logger.info(f"User {db_user.id} deleted product {product_id}")
        await callback.answer("✅ Товар успешно удален!", show_alert=True)
        await show_products_list(callback, db_user, db_session)
    else:
        await callback.answer(
            "Этот товар уже удален или не существует.", show_alert=True
        )


@router.callback_query(F.data.startswith("set_target_"))
async def process_edit_target_start(callback: CallbackQuery, state: FSMContext):
    if not callback.data or not callback.message:
        return

    product_id = int(callback.data.split("_")[-1])
    await state.update_data(edit_product_id=product_id)
    await callback.message.answer("🎯 <b>Введи новую желаемую цену:</b>")
    await state.set_state(EditProductState.waiting_for_target_price)
    await callback.answer()


@router.message(EditProductState.waiting_for_target_price)
async def process_edit_target_finish(
    message: Message, state: FSMContext, db_user: User, db_session
):
    if not message.text:
        return

    try:
        target_price = Decimal(message.text.replace(",", "."))
        if target_price <= 0:
            raise ValueError
    except (ValueError, InvalidOperation):
        await message.answer("⚠️ Пожалуйста, введи корректную цену.")
        return

    data = await state.get_data()
    product_id = data.get("edit_product_id")

    if product_id is None:
        await state.clear()
        return

    stmt = select(Product).where(
        Product.id == product_id, Product.user_id == db_user.id
    )
    result = await db_session.execute(stmt)
    product = result.scalar_one_or_none()

    if product:
        product.target_price = target_price
        await db_session.commit()
        await message.answer(
            f"✅ Желаемая цена для <b>{product.title}</b> обновлена до <b>{target_price:f} ₽</b>"
        )
        await show_products_list(message, db_user, db_session)
    else:
        await message.answer("❌ Товар не найден.")

    await state.clear()


@router.callback_query(F.data.startswith("set_threshold_"))
async def process_edit_threshold_start(callback: CallbackQuery, state: FSMContext):
    if not callback.data or not callback.message:
        return

    product_id = int(callback.data.split("_")[-1])
    await state.update_data(edit_product_id=product_id)
    await callback.message.answer(
        "🎯 <b>Введи порог изменения цены (в рублях):</b>\n\n"
        "<i>Например, если введешь 50, то я буду сообщать об изменениях цены только если она изменится более чем на 50 ₽.</i>"
    )
    await state.set_state(EditProductState.waiting_for_threshold)
    await callback.answer()


@router.message(EditProductState.waiting_for_threshold)
async def process_edit_threshold_finish(
    message: Message, state: FSMContext, db_user: User, db_session
):
    if not message.text:
        return

    try:
        threshold = Decimal(message.text.replace(",", "."))
        if threshold < 0:
            raise ValueError
    except (ValueError, InvalidOperation):
        await message.answer("⚠️ Пожалуйста, введи корректное число.")
        return

    data = await state.get_data()
    product_id = data.get("edit_product_id")

    if product_id is None:
        await state.clear()
        return

    stmt = select(Product).where(
        Product.id == product_id, Product.user_id == db_user.id
    )
    result = await db_session.execute(stmt)
    product = result.scalar_one_or_none()

    if product:
        product.threshold = threshold
        await db_session.commit()
        await message.answer(
            f"✅ Порог уведомлений для <b>{product.title}</b> обновлен до <b>{threshold:f} ₽</b>"
        )
        await show_products_list(message, db_user, db_session)
    else:
        await message.answer("❌ Товар не найден.")

    await state.clear()
