# - *- coding: utf- 8 - *-
from aiogram.dispatcher.middlewares import LifetimeControllerMiddleware

from services.db.services.repository import Repo


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

    async def post_process(self, obj, data, *args):
        if obj is not None and not obj.from_user.is_bot:
            this_user = obj.from_user
        else:
            return

        del data["repo"]
        db = data.get("db")
        if db:
            await db.close()