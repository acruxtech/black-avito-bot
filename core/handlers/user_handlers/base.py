import json

from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.types import CallbackQuery, Message

from services.db.services.repository import Repo
from services.paginator import Paginator
from config import load_config
from core.utils.functions import *
from core.utils.keyboards import *
from core.utils.constants import *

logger = logging.getLogger(__name__)
config = load_config("config.ini")


async def menu(message: Message, state: FSMContext):
    await state.finish()

    await message.answer(
        text="Выберите действие ниже",
        reply_markup=get_start_keyboard()
    )


async def start(message: Message, repo: Repo, state: FSMContext):
    await state.finish()

    user = await repo.get_user_by_telegram_id(message.from_user.id)

    await message.answer(
        text=TEXTS["start"],
        reply_markup=get_start_keyboard() if user and user.is_completed_registration else get_registration_keyboard(),
        parse_mode="html",
    )

    if not user:
        role = 1 if message.from_id in config.tg_bot.admin_ids else 0
        await repo.add_user(
            telegram_id=message.from_id,
            username=message.from_user.username,
            is_tg_premium=message.from_user.is_premium,
            role=role,
        )


async def support(message: Message, state: FSMContext):
    await state.finish()
    await message.answer(TEXTS["support"], parse_mode="html")


def register_user_base_handlers(dp: Dispatcher):
    # base
    dp.register_message_handler(menu, Text("⬅️Назад"), state="*")
    dp.register_message_handler(start, commands=["start"], state="*")

    dp.register_message_handler(support, Text("Поддержка"), state="*")
