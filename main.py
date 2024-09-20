import os
import asyncio
import logging

from aiogram import Bot, Dispatcher
from aiogram.types import BotCommand
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from sqlalchemy.orm import sessionmaker

from config import load_config
from core.filters.role import RoleFilter, AdminFilter
from core.handlers.admin import register_admin
from core.handlers.user import register_user
from core.middlewares.db import DbMiddleware
from core.middlewares.role import RoleMiddleware
from core.middlewares.user_control import UserControlMiddleware
from core.utils.functions import send_db_to_admin
from core.utils.variables import scheduler, bot
from services.db.db_pool import create_db_pool
from services.db.services.repository import Repo

logger = logging.getLogger(__name__)


async def set_commands(bot: Bot):
    commands = [
        BotCommand(command="/start", description="Открыть меню"),
        BotCommand(command="/chat", description="Непрочитанные сообщения"),
    ]
    await bot.set_my_commands(commands)


async def main():
    if os.path.isfile('bot.log'):
        os.remove('bot.log')

    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s - %(levelname)s - %(name)s - %(message)s",
        encoding="UTF-8",
        handlers=[
            logging.FileHandler("bot.log"),
            logging.StreamHandler()
        ]
    )
    logger.error("Starting bot")
    config = load_config("config.ini")

    storage = MemoryStorage()
    db_pool: sessionmaker = await create_db_pool(
        user=config.db.user,
        password=config.db.password,
        address=config.db.address,
        name=config.db.name,
        echo=False,
    )

    await set_commands(bot)
    bot_obj = await bot.get_me()
    logger.info(f"Bot username: {bot_obj.username}")
    dp = Dispatcher(bot, storage=storage)
    dp.middleware.setup(DbMiddleware(db_pool))
    dp.middleware.setup(RoleMiddleware(config.tg_bot.admin_ids))
    dp.middleware.setup(UserControlMiddleware())
    dp.filters_factory.bind(RoleFilter)
    dp.filters_factory.bind(AdminFilter)

    scheduler.start()
    scheduler.add_job(
        send_db_to_admin,
        'cron',
        day=1,
        hour=0,
        minute=0,
        kwargs={
            "bot": bot,
            "repo": Repo(db_pool()),
            "db_admin_ids": config.tg_bot.db_admin_ids,
        }
    )

    register_admin(dp)
    register_user(dp)

    try:
        await dp.start_polling(allowed_updates=["message", "callback_query"])
    finally:
        await dp.storage.close()
        await dp.storage.wait_closed()
        await bot.session.close()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        logger.error("Bot stopped!")
