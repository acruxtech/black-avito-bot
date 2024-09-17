import asyncio
import logging
import random
from contextlib import suppress

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup
from aiogram.utils.exceptions import BotBlocked, InvalidPeerID, ChatNotFound

from core.utils.variables import bot
from services.db.services.repository import Repo

logger = logging.getLogger(__name__)


def get_user_repr(user=None, user_name: int | str = None, job: str = None, price: int = None, skills: str = None,
                  rating: float | int = None):
    if user:
        user_name = user.name
        job = user.job.title
        price = user.price
        skills = user.skills
    text = (f"<b>Никнейм</b>: <code>{user_name}</code>\n\n"
            f"<b>Направление</b>: {job}\n"
            f"<b>Ценовая категория</b>: {'$' * (price + 1)}\n"
            f"<b>Описание услуги</b>: {skills}\n"
            f"<b>Средняя оценка</b>: {round(rating, 1) if rating else '-'}"
            )
    return text


async def send_messages(chat_id: int, msg_id: int, reply_markup: list[list[dict]], filename: str):
    success = 0
    with_error = 0

    msg = await bot.send_message(
        chat_id,
        "Рассылка запущена\n"
        "Успешно: 0, неудачно: 0",
    )

    if reply_markup:
        inline_keyboard = InlineKeyboardMarkup(
            inline_keyboard=[
                [InlineKeyboardButton(text=button["text"], url=button["url"]) for button in row]
                for row in reply_markup
            ]
        )
    else:
        inline_keyboard = None

    with open(filename, "r") as f:
        for user_id in f:
            try:
                user_id = int(user_id)

                await bot.copy_message(
                    user_id,
                    chat_id,
                    msg_id,
                    reply_markup=inline_keyboard
                )
                success += 1
                await asyncio.sleep(0.035)

            except BotBlocked as e:
                logger.error(e)
            except (InvalidPeerID, ChatNotFound) as e:
                logger.error(e)

            except BaseException as e:
                logger.error(e)
                with_error += 1

            finally:
                with suppress(BaseException):
                    if (success + with_error) % 100 == 0:
                        await msg.edit_text(
                            "Рассылка запущена\n"
                            f"Успешно: {success}, неудачно: {with_error}",
                        )

    with suppress(BaseException):
        await msg.edit_text(
            "Рассылка запущена\n"
            f"Успешно: {success}, неудачно: {with_error}"
        )
    await bot.send_message(
        chat_id,
        "Рассылка завершена"
    )


def get_user_rating(deals):
    if deals:
        rating = sum(deal.rating for deal in deals) / len(deals)
    else:
        rating = None
    return rating


async def get_db_file(repo):
    with open("users.txt", "w") as f:
        users_telegram_ids = await repo.get_users_telegram_ids()
        users_ids = await repo.get_users_ids()
        users_usernames = await repo.get_users_usernames()

        for user_id, telegram_id, username in zip(users_ids, users_telegram_ids, users_usernames):
            f.write(f"{user_id} - {telegram_id} - @{username}\n")


async def send_db_to_admin(bot: Bot, repo: Repo, db_admin_ids: list[int]):
    await get_db_file(repo)
    with open("users.txt", "r") as f:
        for user_id in db_admin_ids:
            await bot.send_document(user_id, f)
