import json

from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.types import CallbackQuery, Message, ParseMode
from aiogram.utils.exceptions import BadRequest

from core.states.Anon import Anon
from services.db.services.repository import Repo
from services.paginator import Paginator
from config import load_config
from core.utils.functions import *
from core.utils.keyboards import *
from core.utils.constants import *

logger = logging.getLogger(__name__)
config = load_config("config.ini")


async def anon(call: CallbackQuery, repo: Repo, state: FSMContext):
    user_id = int(call.data.split("_")[-1])
    await call.answer()

    user = await repo.get_user_by_id(user_id)
    me = await repo.get_user_by_telegram_id(call.from_user.id)
    await call.message.answer("Чат начат. Можете отправлять сообщения. Затем нажмите кнопку завершения диалога "
                              "или войдите в другой раздел",
                              reply_markup=get_cancel_keyboard("anon", "Завершить чат"))
    await state.update_data(to_telegram_id=user.telegram_id, me_id=me.id)
    await state.set_state(Anon.here_message)


async def anon_here_message(message: Message, repo: Repo, state: FSMContext):
    data = await state.get_data()
    is_first_msg = data.get("is_first_msg", True)
    try:
        if is_first_msg:
            await message.bot.send_message(
                chat_id=data["to_telegram_id"],
                text=f"Новое сообщение от пользователя <code>{data['me_id']}</code>",
                parse_mode="html",
                reply_markup=get_start_chat_keyboard(data['me_id']),
            )
            await state.update_data(is_first_msg=False)

        await message.bot.copy_message(
            chat_id=data["to_telegram_id"],
            from_chat_id=message.chat.id,
            message_id=message.message_id,
        )
    except ValueError:
        await message.answer("Не удалось доставить сообщение. Вероятнее всего, человек заблокировал бота")
        return


async def cancel_anon(call: CallbackQuery, state: FSMContext):
    await state.finish()
    await call.answer()
    await call.message.answer("Чат завершен.")


async def start_chat(call: CallbackQuery, repo: Repo, state: FSMContext):
    with_id = int(call.data.split("_")[-1])
    to_user = await repo.get_user_by_id(with_id)
    me = await repo.get_user_by_telegram_id(call.from_user.id)

    await call.answer()
    await call.message.answer(text="Чат начат. Можете отправлять сообщения. Затем нажмите кнопку завершения диалога "
                                   "или войдите в другой раздел",
                                   reply_markup=get_cancel_keyboard("anon", "Завершить чат"))
    await state.update_data(to_telegram_id=to_user.telegram_id, me_id=me.id)
    await state.set_state(Anon.here_message)


def register_user_anon_handlers(dp: Dispatcher):
    dp.register_callback_query_handler(anon, Text(startswith="anon"), state="*")
    dp.register_message_handler(anon_here_message, content_types=["any"], state=Anon.here_message)
    dp.register_callback_query_handler(cancel_anon, Text(startswith="cancel_anon"), state=Anon.here_message)

    dp.register_callback_query_handler(start_chat, Text(startswith="start_chat"), state="*")

