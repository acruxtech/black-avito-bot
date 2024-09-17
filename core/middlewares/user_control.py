# - *- coding: utf- 8 - *-
import datetime

from aiogram.dispatcher.handler import CancelHandler
from aiogram.dispatcher.middlewares import LifetimeControllerMiddleware

from config import load_config
from core.utils.constants import TECH_WORK_START_HOUR, TECH_WORK_END_HOUR, TECH_WORK_START_MINUTE, TECH_WORK_END_MINUTE
from services.db.services.repository import Repo


config = load_config("config.ini")


class UserControlMiddleware(LifetimeControllerMiddleware):
    skip_patterns = ["error", "update"]

    def __init__(self):
        super().__init__()

    async def pre_process(self, obj, data, *args):
        if obj is not None and not obj.from_user.is_bot:
            this_user = obj.from_user
        else:
            return

        repo: Repo = data["repo"]

        user = await repo.add_user(
            telegram_id=this_user.id,
            username=this_user.username,
            is_tg_premium=this_user.is_premium,
        )

        time = datetime.datetime.now()
        if (
            TECH_WORK_START_HOUR <= time.hour <= TECH_WORK_END_HOUR and
            TECH_WORK_START_MINUTE <= time.minute <= TECH_WORK_END_MINUTE and
            user.telegram_id not in config.tg_bot.admin_ids
        ):
            await obj.bot.send_message(
                user.telegram_id,
                f"Технические работы с {str(TECH_WORK_START_HOUR).zfill(2)}:{str(TECH_WORK_START_MINUTE).zfill(2)} до "
                f"{str(TECH_WORK_END_HOUR).zfill(2)}:{str(TECH_WORK_END_MINUTE).zfill(2)}. Попробуйте позже"
            )
            raise CancelHandler()

    async def post_process(self, obj, data, *args):
        if obj is not None and not obj.from_user.is_bot:
            this_user = obj.from_user
        else:
            return

        del data["repo"]
        db = data.get("db")
        if db:
            await db.close()