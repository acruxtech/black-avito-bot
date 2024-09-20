import json
import os
from datetime import datetime

from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.types import CallbackQuery, Message, ParseMode
from aiogram.utils.exceptions import BadRequest

from core.models.AnonChat import AnonChat
from core.states.Anon import Anon
from services.db.services.repository import Repo
from services.paginator import Paginator
from config import load_config
from core.utils.functions import *
from core.utils.keyboards import *
from core.utils.constants import *

logger = logging.getLogger(__name__)
config = load_config("config.ini")


async def chat(message: Message, repo: Repo, state: FSMContext):
    await state.finish()

    unread_messages = await repo.get_user_unread_messages(message.from_id)
    if not unread_messages:
        return await message.answer("Непрочитанных сообщений нет")

    chats = []
    handled_ids = []
    for unread_message in unread_messages:
        if unread_message.from_telegram_id in handled_ids:
            continue
        from_user = await repo.get_user_by_telegram_id(unread_message.from_telegram_id)
        chats.append(
            AnonChat(
                from_user.id,
                from_user.name,
                len([
                    unread_message for unread_message in unread_messages
                    if unread_message.from_telegram_id == from_user.telegram_id
                ])
            )
        )
        handled_ids.append(unread_message.from_telegram_id)

    await message.answer("У вас есть сообщения с:", reply_markup=get_unread_message_keyboard(chats))


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
    try:
        await repo.add_unread_message(message.from_user.id, data["to_telegram_id"], message.message_id)
        to_user = await repo.get_user_by_telegram_id(data["to_telegram_id"])
        from_user = await repo.get_user_by_telegram_id(message.from_user.id)
        names = [to_user.name, from_user.name]
        names.sort()
        if not os.path.exists(f"chats/{names[0]}-{names[1]}"):
            os.mkdir(f"chats/{names[0]}-{names[1]}")
        if message.text:
            if os.path.exists(f"chats/{names[0]}-{names[1]}/messages.txt"):
                with open(f"chats/{names[0]}-{names[1]}/messages.txt", 'a', encoding='utf-8') as f:
                    f.write(f'{from_user.name}: {message.text}\n')
            else:
                with open(f"chats/{names[0]}-{names[1]}/messages.txt", "w", encoding='utf-8') as f:
                    f.write(f'{from_user.name}: {message.text}\n')
        dt = datetime.now()
        if message.video:
            await message.video.download(
                destination_file=f"chats/{names[0]}-{names[1]}/{dt.strftime('%d.%m.%Y %H:%M:%S')}-{message.video.file_id}"
            )
        if message.photo:
            for photo in message.photo:
                await photo.download(
                    destination_file=f"chats/{names[0]}-{names[1]}/{dt.strftime('%d.%m.%Y %H:%M:%S')}.png"
                )
        if message.voice:
            await message.audio.download(
                destination_file=f"chats/{names[0]}-{names[1]}/{dt.strftime('%d.%m.%Y %H:%M:%S')}.ogg"
            )
        if message.document:
            await message.document.download(
                destination_file=f"chats/{names[0]}-{names[1]}/{dt.strftime('%d.%m.%Y %H:%M:%S')}-{message.document.file_name}"
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

    unread_messages = await repo.get_user_unread_messages(call.from_user.id)
    for unread_message in unread_messages:
        await call.bot.copy_message(
            chat_id=call.from_user.id,
            from_chat_id=unread_message.from_telegram_id,
            message_id=unread_message.message_id,
        )
        await repo.delete_unread_message(unread_message.message_id)

    await state.update_data(to_telegram_id=to_user.telegram_id, me_id=me.id)
    await state.set_state(Anon.here_message)


def register_user_anon_handlers(dp: Dispatcher):
    dp.register_message_handler(chat, commands=["chat"], state="*")

    dp.register_callback_query_handler(anon, Text(startswith="anon"), state="*")
    dp.register_message_handler(anon_here_message, content_types=["any"], state=Anon.here_message)
    dp.register_callback_query_handler(cancel_anon, Text(startswith="cancel_anon"), state=Anon.here_message)

    dp.register_callback_query_handler(start_chat, Text(startswith="start_chat"), state="*")
