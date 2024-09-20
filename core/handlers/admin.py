import json
from datetime import datetime

from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.types import Message, CallbackQuery

from services.db.models import User
from core.models.role import UserRole
from core.states.admin import *
from core.utils.functions import *
from core.utils.keyboards import *
from core.utils.constants import *
from core.utils.variables import scheduler
from services.db.services.repository import Repo

logger = logging.getLogger(__name__)


async def admin_menu(message: Message, state: FSMContext):
    await message.answer("Админ-панель открыта", reply_markup=get_admin_keyboard())
    await state.finish()


async def admin_menu_call(call: CallbackQuery, state: FSMContext):
    await call.message.answer("Выберите действие", reply_markup=get_admin_keyboard())
    await call.answer()
    await state.finish()


async def statistics(call: CallbackQuery, state: FSMContext, repo: Repo):
    all_users = await repo.get_amount_users()
    complete_registration_users = await repo.get_amount_completed_registration_users()
    tg_premium_users = await repo.get_amount_tg_premium_users()

    text = (
        f"Всего в боте: {all_users}\n"
        f"Прошли регистрацию: {complete_registration_users} ({complete_registration_users / all_users * 100:.2f}%)\n"
        f"Не прошли регистрацию: {all_users - complete_registration_users} "
        f"({(all_users - complete_registration_users) / all_users * 100:.2f}%)\n"
        f"Телеграм-премуим пользователей: {tg_premium_users} ({tg_premium_users / all_users * 100:.2f}%)\n"
        f"Заблокировали бота: {await repo.get_amount_blocked_users()}"
    )

    await call.answer()
    await call.message.answer(text, parse_mode="html")
    await state.finish()


async def mailing(callback: CallbackQuery):
    await callback.message.answer("Настройки⚙️ рассылок", reply_markup=get_mailing_keyboard())
    await callback.answer()


async def create_mailing(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer(
        "Отправьте время рассылки в формате YYYY.MM.DD HH:MM (например, 2024.10.31 12:00) или точку \".\", чтобы "
        "отправить сразу же",
        reply_markup=get_back_to_admin_keyboard(),
    )
    await callback.answer()
    await state.set_state(Mailing.here_time.state)
    

async def mailing_here_time(message: Message, state: FSMContext):
    data = {}

    try:
        if message.text == ".":
            data["date"] = datetime.now()
        else:
            data["date"] = datetime.strptime(message.text, "%Y.%m.%d %H:%M")
        await state.set_data(data)
    except BaseException as e:
        logger.error(e)
        return await message.answer("Неправильный формат ввода! Попробуйте еще раз")
    
    await message.answer("Отправьте пост для рассылки")
    await state.set_state(Mailing.forward_post.state)


async def mailing_here_post(message: Message, state: FSMContext):
    data = await state.get_data()
    data["chat_id"] = message.chat.id
    data["msg_id"] = message.message_id

    if message.reply_markup: 
        inline_keyboard_json = [
            [{"text": button.text, "url": button.url} for button in row]
            for row in message.reply_markup.inline_keyboard
        ]
    else:
        inline_keyboard_json = None

    data["reply_markup"] = inline_keyboard_json
    await state.set_data(data)

    await message.bot.copy_message(
        message.chat.id,
        message.chat.id,
        message.message_id,
        reply_markup=message.reply_markup,
    )

    await message.answer(
        f"Подтвердить запланирование рассылки на {data['date']}?",
        reply_markup=get_apply_mailing_keyboard()
    )
    await state.set_state(Mailing.apply.state)


async def apply_mailing(callback: CallbackQuery, state: FSMContext, repo: Repo):
    data = await state.get_data() 

    user_ids = await repo.get_users_telegram_ids()
    filename = f"mailing_{data['date']}.txt"
    with open(filename, "w") as f:
        for user_id in user_ids:
            f.write(f"{user_id}\n")

    scheduler.add_job(
        send_messages,
        "date",
        kwargs={
            "chat_id": data["chat_id"],
            "msg_id": data["msg_id"],
            "reply_markup": data["reply_markup"],
            "filename": filename,
        },
        run_date=data["date"],
        jobstore='mongo',
        misfire_grace_time=1000,
        coalesce=True,
    )

    await callback.message.answer("Рассылка запланирована")
    await callback.answer()
    await state.finish()


async def cancel_create_mailing(callback: CallbackQuery, state: FSMContext):
    mailing_id = callback.data.split("_")[-1]
    if mailing_id != "mailing":
        scheduler.remove_job(mailing_id)
    await callback.message.answer("Рассылка отменена")
    await callback.answer()
    await state.finish()


async def cancel_mailing(callback: CallbackQuery):
    await callback.answer()
    buttons = [
        InlineKeyboardButton(
            text=task.next_run_time.strftime("%Y.%m.%d %H:%M"),
            callback_data=f"cancel_mailing_{task.id}"
        )
        for task in scheduler.get_jobs(jobstore="mongo")
    ]
    keyboard = InlineKeyboardMarkup()
    keyboard.add(*buttons)
    keyboard.row_width = 1
    await callback.message.answer(
        "Выберите рассылку, которую надо удалить",
        reply_markup=keyboard,
    )


async def export(callback: CallbackQuery, state: FSMContext, repo: Repo):
    await get_db_file(repo)

    with open("users.txt", "r") as f:
        await callback.message.answer_document(f)
    
    await callback.answer()
    await state.finish()


async def settings(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Админ-панель открыта", reply_markup=get_settings_keyboard())
    await callback.answer()
    await state.finish()


async def job_settings(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Выберите действие", reply_markup=get_job_settings_keyboard())
    await callback.answer()
    await state.finish()


async def add_job(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Отправьте название деятельности")
    await callback.answer()
    await state.set_state(AddJob.here_title.state)


async def add_job_here_title(message: Message, state: FSMContext, repo: Repo):
    await repo.add_job(message.text)
    await message.answer("Деятельность успешно добавлена")
    await state.finish()


async def change_job(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Отправьте текущее название деятельности")
    await callback.answer()
    await state.set_state(ChangeJob.here_title.state)


async def change_job_here_current_title(message: Message, state: FSMContext):
    await state.update_data(curr_title=message.text)
    await message.answer("Отправьте новое название деятельности")
    await state.set_state(ChangeJob.here_new_title.state)


async def change_job_here_new_title(message: Message, state: FSMContext, repo: Repo):
    data = await state.get_data()
    curr_title = data["curr_title"]
    await repo.update_job(curr_title=curr_title, title=message.text)
    await message.answer("Деятельность успешно изменена")
    await state.finish()


async def delete_job(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Отправьте название деятельности для ее удаления")
    await callback.answer()
    await state.set_state(DeleteJob.here_title.state)


async def delete_job_here_title(message: Message, state: FSMContext, repo: Repo):
    try:
        await repo.delete_job(message.text)
    except ValueError as e:
        logger.error(e)
        return await message.answer("Деятельности с таким названием нет")
    await message.answer("Деятельность успешно удалена")
    await state.finish()


async def check_deal(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Отправьте id")
    await callback.answer()
    await state.set_state(DealSettings.here_id.state)


async def deal_here_id(message: Message, repo: Repo, state: FSMContext):
    await state.finish()

    deal_id = int(message.text)
    deal = await repo.get_deal_by_id(deal_id)
    if not deal:
        return await message.answer("Сделки с таким id нет")
    
    await message.answer(
        TEXTS["deal_info"].format(
            id=deal.id,
            is_confirmed_by_executor=("не " if not deal.is_confirmed_by_executor else "") + "подтверждена исполнителем",
            client_id=deal.client_id,
            executor_id=deal.executor_id,
            amount=deal.amount,
            conditions=deal.conditions,
            is_completed="да" if deal.is_completed else "нет",
        ),
        parse_mode="html",
    )


async def user_settings(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Отправьте id пользователя", reply_markup=get_empty_keyboard())
    await callback.answer()
    await state.set_state(UserSettings.here_id.state)


async def user_settings_here_id(message: Message, repo: Repo, state: FSMContext):
    try:
        user = await repo.get_user_by_telegram_id(int(message.text))
    except ValueError:
        return await message.answer("Неверный формат. Попробуйте еще раз")
    
    if user is None:
        return await message.answer("Пользователь не найден")

    await message.answer(
        text=f"<b>telegram id:</b> <code>{user.telegram_id}</code>\n"
        f"<b>id:</b> <code>{user.id}</code>\n"
        f"<b>Юзернейм:</b> @{user.username}\n"
        f"<b>Заблокировал бота:</b> {'да' if user.is_bot_blocked else 'нет'}\n"
        f"<b>Завершил регистрацию:</b> {'да' if user.is_completed_registration else 'нет'}\n"
        f"<b>Телеграм-премиум:</b> {'да' if user.is_tg_premium else 'нет'}\n"
        f"<b>Анкета скрыта:</b> {'да' if user.is_shadow_ban else 'нет'}\n"
        f"<b>Баланс:</b> {user.balance}\n"
        f"<b>Направление</b>: {user.job.title if user.job else '-'}\n"
        f"<b>Ценовая категория</b>: {'$' * (user.price + 1) if user.price else '-'}\n"
        f"<b>Описание услуги</b>: {user.skills if user.skills else '-'}\n",
        parse_mode="html",
        reply_markup=get_user_settings_keyboard(user.is_shadow_ban)
    )
    await state.set_state(UserSettings.here_action.state)
    await state.update_data(db_user=user)


async def user_balance(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.answer(
        text="Отправьте, насколько надо изменить баланс (число без знака - чтобы увеличить, число с минусом,"
             "чтобы уменьшить)\n\nПример:\n<code>5000</code> - добавит 5000$ на счет человека\n"
             "<code>-100</code> - уберет 100$ с баланса человека",
        parse_mode="html",    
    )
    await state.set_state(UserSettings.here_balance_amount.state)


async def user_balance_here_amount(message: Message, repo: Repo, state: FSMContext):
    data = await state.get_data()
    user: User = data["db_user"]

    try: 
        amount = int(message.text)
    except ValueError:
        return await message.answer("Некорректное значение. Попробуйте еще раз")

    await repo.update_user(telegram_id=user.telegram_id, balance=user.balance + amount)
    await message.answer("Баланс успешно изменен")
    await state.set_state(UserSettings.here_action.state)


async def user_deals(call: CallbackQuery, repo: Repo, state: FSMContext):
    await call.answer()

    data = await state.get_data()
    user: User = data["db_user"]
    deals = await repo.get_user_deals(user.id)

    for deal in deals:
        await call.message.answer(
            TEXTS["deal_info"].format(
                id=deal.id,
                is_confirmed_by_executor=("не " if not deal.is_confirmed_by_executor else "") + "подтверждена "
                                                                                                "исполнителем",
                client_id=deal.client_id,
                executor_id=deal.executor_id,
                amount=deal.amount,
                conditions=deal.conditions,
                is_completed="да" if deal.is_completed else "нет",
            ),
            parse_mode="html",
        )


async def user_message(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.answer(
        "Напишите сообщение, которое необходимо отправить человеку",
        parse_mode="html",    
    )
    await state.set_state(UserSettings.here_message_text.state)


async def user_message_here_text(message: Message, state: FSMContext):
    data = await state.get_data()
    user: User = data["db_user"]

    try:
        await message.bot.send_message(
            user.telegram_id,
            "❗<b>Вам пришло сообщение от администратора</b>❗",
            parse_mode="html",
        )
        await message.bot.copy_message(
            user.telegram_id,
            message.chat.id,
            message.message_id,
        )
    except BaseException:
        return await message.answer("Не удалось отправить сообщение. Пользователь заблокировал бота")

    await message.answer("Сообщение отправлено")
    await state.set_state(UserSettings.here_action.state)


async def user_ban(call: CallbackQuery, repo: Repo, state: FSMContext):
    data = await state.get_data()
    user: User = data["db_user"]
    prev_val = user.is_shadow_ban

    user = await repo.update_user(telegram_id=user.telegram_id, is_shadow_ban=not prev_val)
    await state.update_data(db_user=user)
    with suppress(BaseException):
        await call.message.edit_reply_markup(
            reply_markup=get_user_settings_keyboard(not prev_val)
        )
    await call.answer("Успешно")


async def user_action(call: CallbackQuery, repo: Repo):
    await call.answer()

    action = call.data.split("_")[-2]
    user_id = int(call.data.split("_")[-1])

    if action == "apply":
        user = await repo.update_user(user_id=user_id, is_shadow_ban=False)
        await call.bot.send_message(
            chat_id=user.telegram_id,
            text="Ваша анкета была подтверждена администратором и теперь показывается в разделе 'Услуги💼'"
        )
    elif action == "decline":
        user = await repo.get_user_by_id(user_id)
        await call.bot.send_message(
            chat_id=user.telegram_id,
            text="Ваша анкета не была подтверждена администратором :( Пройдите еще регистарцию еще раз",
            reply_markup=get_registration_keyboard(),
        )


async def cancel_deal(callback: CallbackQuery, state: FSMContext):
    await callback.message.answer("Отправьте id сделки")
    await callback.answer()
    await state.set_state(CancelDeal.here_id.state)


async def cancel_deal_here_id(message: Message, state: FSMContext):
    await state.update_data(deal_id=int(message.text))
    await message.answer(
        "Перевести замороженные средства исполнителю или вернуть на счет заказчика",
        reply_markup=get_yes_no_keyboard("money_solution")
    )
    await state.set_state(CancelDeal.here_money_solution.state)


async def cancel_deal_here_money_solution(call: CallbackQuery, repo: Repo, state: FSMContext):
    money_solution = call.data.split("_")[-1]
    await call.answer()

    data = await state.get_data()
    deal = await repo.get_deal_by_id(data["deal_id"])
    await repo.update_deal(deal.id, is_completed=True)

    if money_solution == "yes":
        user = await repo.get_user_by_id(deal.executor_id)
        client = await repo.get_user_by_id(deal.client_id)
        with suppress(BaseException):
            await call.bot.send_message(
                user.telegram_id,
                f"Сделка (id: {deal.id}) завершена администратором. Деньги переведены вам на счет"
            )
        with suppress(BaseException):
            await call.bot.send_message(
                client.telegram_id,
                f"Сделка (id: {deal.id}) завершена администратором. Деньги переведены на счет исполнителя"
            )
    else:
        user = await repo.get_user_by_id(deal.client_id)
        executor = await repo.get_user_by_id(deal.executor_id)
        with suppress(BaseException):
            await call.bot.send_message(
                user.telegram_id,
                f"Сделка (id: {deal.id}) завершена администратором. Деньги возвращены вам на счет"
            )
        with suppress(BaseException):
            await call.bot.send_message(
                executor.telegram_id,
                f"Сделка (id: {deal.id}) завершена администратором без перевода средств вам"
            )
    await repo.update_user(
        telegram_id=user.telegram_id,
        balance=user.balance + deal.amount,
    )
    await call.message.answer("Сделка завершена")
    await state.finish()


async def start_payment(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.answer(
        "Отправьте значение в $, которое необходимо будет платить для регистрации в качестве исполнителя. "
        "Чтобы отключить стартовый взнос, введите 0",
        parse_mode="html",
    )
    await state.set_state(StartPayment.here_amount.state)


async def start_payment_here_amount(message: Message, state: FSMContext):
    with open('settings.json', 'r') as file:
        data = json.load(file)
    data["start_payment"] = int(message.text)
    with open('settings.json', 'w') as file:
        json.dump(data, file)
    await message.answer("Готово")
    await state.finish()


def register_admin(dp: Dispatcher):
    # base
    dp.register_message_handler(admin_menu, commands="admin", state="*", role=UserRole.OWNER)
    dp.register_callback_query_handler(admin_menu_call, Text("admin"), state="*", role=UserRole.OWNER)
    dp.register_callback_query_handler(statistics, Text("statistics"), state="*", role=UserRole.OWNER)
    dp.register_callback_query_handler(mailing, Text("mailing"), state="*", role=UserRole.OWNER)
    dp.register_callback_query_handler(create_mailing, Text("create_mailing"), state="*", role=UserRole.OWNER)
    dp.register_message_handler(mailing_here_time, state=Mailing.here_time, role=UserRole.OWNER)
    dp.register_message_handler(mailing_here_post, content_types=["any"], state=Mailing.forward_post,
                                role=UserRole.OWNER)
    dp.register_callback_query_handler(apply_mailing, Text("apply_mailing"), state=Mailing.apply, role=UserRole.OWNER)
    dp.register_callback_query_handler(cancel_create_mailing, Text(startswith="cancel_mailing"), state="*",
                                       role=UserRole.OWNER)
    dp.register_callback_query_handler(cancel_mailing, Text("delete_mailing"), state="*", role=UserRole.OWNER)
    dp.register_callback_query_handler(export, Text("export"), state="*", role=UserRole.OWNER)
    dp.register_callback_query_handler(settings, Text("settings"), state="*", role=UserRole.OWNER)

    # job
    dp.register_callback_query_handler(job_settings, Text("job_settings"), state="*", role=UserRole.OWNER)
    dp.register_callback_query_handler(add_job, Text("add_job"), state="*", role=UserRole.OWNER)
    dp.register_message_handler(add_job_here_title, state=AddJob.here_title, role=UserRole.OWNER)
    dp.register_callback_query_handler(change_job, Text("change_job"), state="*", role=UserRole.OWNER)
    dp.register_message_handler(change_job_here_current_title, state=ChangeJob.here_title, role=UserRole.OWNER)
    dp.register_message_handler(change_job_here_new_title, state=ChangeJob.here_new_title, role=UserRole.OWNER)
    dp.register_callback_query_handler(delete_job, Text("delete_job"), state="*", role=UserRole.OWNER)
    dp.register_message_handler(delete_job_here_title, state=DeleteJob.here_title, role=UserRole.OWNER)

    # user
    dp.register_callback_query_handler(user_settings, Text("user_settings"), state="*", role=UserRole.OWNER)
    dp.register_message_handler(user_settings_here_id, state=UserSettings.here_id, role=UserRole.OWNER)
    dp.register_callback_query_handler(user_balance, Text("user_balance"), state=UserSettings.here_action,
                                       role=UserRole.OWNER)
    dp.register_message_handler(user_balance_here_amount, state=UserSettings.here_balance_amount, role=UserRole.OWNER)
    dp.register_callback_query_handler(user_deals, Text("user_deals"), state=UserSettings.here_action,
                                       role=UserRole.OWNER)
    dp.register_callback_query_handler(user_message, Text("user_message"), state=UserSettings.here_action,
                                       role=UserRole.OWNER)
    dp.register_message_handler(user_message_here_text, state=UserSettings.here_message_text, role=UserRole.OWNER)
    dp.register_callback_query_handler(user_ban, Text("user_ban"), state=UserSettings.here_action, role=UserRole.OWNER)

    dp.register_callback_query_handler(start_payment, Text("start_payment"), state="*", role=UserRole.OWNER)
    dp.register_message_handler(start_payment_here_amount, state=StartPayment.here_amount, role=UserRole.OWNER)
    
    # deal
    dp.register_callback_query_handler(check_deal, Text("check_deal"), state="*", role=UserRole.OWNER)
    dp.register_message_handler(deal_here_id, state=DealSettings.here_id, role=UserRole.OWNER)
    dp.register_callback_query_handler(cancel_deal, Text("cancel_deal"), state="*", role=UserRole.OWNER)
    dp.register_message_handler(cancel_deal_here_id, state=CancelDeal.here_id, role=UserRole.OWNER)
    dp.register_callback_query_handler(cancel_deal_here_money_solution, Text(startswith="money_solution"), state=CancelDeal.here_money_solution, role=UserRole.OWNER)


    # user apply
    dp.register_callback_query_handler(user_action, Text(startswith="new_user"), state="*", role=UserRole.OWNER)
