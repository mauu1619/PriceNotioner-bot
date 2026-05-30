from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from loguru import logger

from src.bot.keyboards.main_menu import get_main_menu

router = Router(name="basic_commands")


@router.message(CommandStart())
async def cmd_start(message: Message):
    logger.info(f"User {message.chat.id} issued /start command.")
    await message.answer(
        "👋 <b>Привет! Добро пожаловать в парсер-бота!</b> 🛍\n\n"
        "Я помогу тебе отслеживать цены на твои любимые товары и сообщу, когда они подешевеют 📉.\n\n"
        "💡 <i>Нажми /help, если нужна подробная инструкция.</i>\n\n"
        "👇 Выбери действие в меню ниже:",
        reply_markup=get_main_menu(),
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    logger.info(f"User {message.chat.id} issued /help command.")
    await message.answer(
        "🤖 <b>Как это работает?</b>\n\n"
        "1️⃣ Отправь мне ссылку или артикул на товар с маркетплейса (сейчас поддерживается Wildberries).\n"
        "2️⃣ Укажи желаемую цену, которую готов заплатить.\n"
        "3️⃣ Занимайся своими делами, а я буду следить за ценой! Как только она упадет, я сразу пришлю тебе уведомление 🔔."
    )
