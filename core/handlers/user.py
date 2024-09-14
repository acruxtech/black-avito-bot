from aiogram import Dispatcher

from core.handlers.user_handlers.anon import register_user_anon_handlers
from core.handlers.user_handlers.base import register_user_base_handlers
from core.handlers.user_handlers.profile import register_user_profile_handlers
from core.handlers.user_handlers.rialto import register_user_rialto_handlers


def register_user(dp: Dispatcher):
    register_user_base_handlers(dp)
    register_user_profile_handlers(dp)
    register_user_rialto_handlers(dp)
    register_user_anon_handlers(dp)