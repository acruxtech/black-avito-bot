import logging

from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.types import Message, CallbackQuery, InlineKeyboardButton

from core.states.Rating import Rating
from core.states.Tip import Tip
from core.utils.constants import PRICE_MAPPER, FEE, TEXTS
from core.utils.functions import get_user_repr, get_user_rating
from services.db.services.repository import Repo
from config import load_config
from core.states.CreateDeal import CreateDeal
from core.states.Rialto import Rialto
from core.utils.keyboards import *
from services.paginator import Paginator

logger = logging.getLogger(__name__)
config = load_config("config.ini")


async def rialto(message: Message, repo: Repo, state: FSMContext):
    jobs = await repo.get_jobs()
    paginator = Paginator(
        data=[
            [InlineKeyboardButton(text=job.title, callback_data=f"job_{job.id}")]
            for job in jobs
        ],
        dp=Dispatcher.get_current(),
        state=Rialto.here_job,
        size=10,
    )
    await message.answer(
        "Выберите интересующее направление",
        reply_markup=paginator(),
    )
    await state.set_state(Rialto.here_job)


async def rialto_here_job(call: CallbackQuery, state: FSMContext):
    await call.answer()
    job_id = call.data.split("_")[-1]
    await state.update_data(job_id=job_id)
    await call.message.answer(
        text="Выберите ценовую категорию",
        parse_mode="html",
        reply_markup=get_price_keyboard(),
    )
    await state.set_state(Rialto.here_price)


async def rialto_here_price(call: CallbackQuery, repo: Repo, state: FSMContext):
    data = await state.get_data()
    await call.answer()

    price = call.data.split("_")[-1]
    users = await repo.get_users_where(
        job_id=int(data["job_id"]),
        price=PRICE_MAPPER[price],
        is_shadow_ban=False,
    )
    if not users:
        await call.message.answer("Доступных предложений в этом разделе и в этой ценовой категории нет.")
        return
    users.sort(key=lambda user: user.priority, reverse=True)
    await state.update_data(user_ids=[user.id for user in users])
    deals = await repo.get_user_executor_completed_deals(users[0].id)
    await call.message.answer(
        text=f"Предложение 1/{len(users)}\n\n" if not users[0].is_highlight else f"<b><i>Предложение 1/{len(users)}</i></b>\n\n" +
        get_user_repr(
            users[0],
            rating=get_user_rating(deals),
            summ=sum(deal.amount for deal in deals)
        ),
        parse_mode="html",
        reply_markup=get_scroll_keyboard(
            additional_button=types.InlineKeyboardButton(text="Создать сделку",
                                                         callback_data=f"create_deal_{users[0].id}"),
            forward=f"user_1" if len(users) > 1 else None
        ),
    )
    await state.set_state(Rialto.swap)


async def user_info(call: CallbackQuery, repo: Repo, state: FSMContext):
    await call.answer()
    data = await state.get_data()
    user_ids = data["user_ids"]
    user_number = int(call.data.split("_")[-1])

    user = await repo.get_user_by_id(user_ids[user_number])
    deals = await repo.get_user_executor_completed_deals(user_ids[user_number])
    await call.message.edit_text(
        text=f"Предложение {user_number + 1}/{len(user_ids)}\n\n" if not user.is_highlight else f"<b><i>Предложение {user_number + 1}/{len(user_ids)}</i></b>\n\n" +
        get_user_repr(
            user,
            rating=get_user_rating(deals),
            summ=sum(deal.amount for deal in deals)
        ),
        parse_mode="html",
        reply_markup=get_scroll_keyboard(
            back=f"user_{user_number - 1}" if user_number > 0 else None,
            additional_button=types.InlineKeyboardButton(text="Создать сделку", callback_data=f"create_deal_{user.id}"),
            forward=f"user_{user_number + 1}" if user_number < len(user_ids) - 1 else None
        ),
    )


async def guarantee(message: Message, state: FSMContext):
    await state.finish()

    await message.answer(
        text="Выберите действие ниже",
        reply_markup=get_guarantee_keyboard()
    )


async def create_deal(call: CallbackQuery, state: FSMContext):
    await call.answer()

    await call.message.answer("Отправьте никнейм человека, с которым хотите заключить сделку")
    await state.set_state(CreateDeal.here_executor_id)


async def create_deal_here_executor_id(message: Message, repo: Repo, state: FSMContext):
    executor = await repo.get_user_by_name(message.text)
    if not executor:
        return await message.answer("Этого пользователя нет в боте. Убедитесь, что вы правильно ввели никнейм")

    if executor.is_bot_blocked:
        return await message.answer("Этот пользователь заблокировал бота.")

    await state.update_data(executor_id=executor.id)

    await message.answer(
        "Хорошо. Отправьте сумму сделки в $. Она будет заморожена на вашем счете "
        f"после подтверждения сделки исполнителем. Также, будет списана комиссия сервиса {FEE * 100}%"
    )
    await state.set_state(CreateDeal.here_amount)


async def create_deal_here_executor_id_callback(call: CallbackQuery, repo: Repo, state: FSMContext):
    executor_id = int(call.data.split("_")[-1])
    await call.answer()

    executor = await repo.get_user_by_id(executor_id)
    if executor.is_bot_blocked:
        return await call.message.answer("Этот пользователь заблокировал бота.")

    await state.finish()
    await state.update_data(executor_id=executor_id)

    await call.message.answer(
        "Хорошо. Отправьте сумму сделки в $. Она будет заморожена на вашем счете "
        f"после подтверждения сделки исполнителем. Также, будет списана комиссия сервиса {FEE * 100}%"
    )
    await state.set_state(CreateDeal.here_amount)


async def create_deal_here_amount(message: Message, repo: Repo, state: FSMContext):
    try:
        amount = int(message.text)
    except ValueError:
        return await message.answer("Сумма должна быть числом")

    me = await repo.get_user_by_telegram_id(message.from_id)
    if me.balance < amount * (1 + FEE):
        return await message.answer("Недостаточный баланс. Пополните или отправьте другую сумму")

    await state.update_data(amount=amount)

    await message.answer(
        "Теперь отправьте условия сделки. Заранее согласуйте их с исполнителем. "
        "Это необходимо для разрешения спорных ситуаций администратором в случае их возникновения"
    )
    await state.set_state(CreateDeal.here_conditions)


async def create_deal_here_conditions(message: Message, repo: Repo, state: FSMContext):
    await state.update_data(conditions=message.parse_entities(as_html=True))
    data = await state.get_data()
    client = await repo.get_user_by_telegram_id(message.from_id)
    executor = await repo.get_user_by_id(data["executor_id"])
    await message.answer("Ваша сделка:")
    await message.answer(
        text=TEXTS["deal_info"].format(
            id="создается",
            is_confirmed_by_executor="не подтверждена исполнителем",
            client_name=client.name,
            executor_name=executor.name,
            amount=data["amount"],
            conditions=data["conditions"],
            is_completed="нет",
        ),
        reply_markup=get_apply_deal_keyboard(),
        parse_mode="html",
    )


async def apply_creating_deal(call: CallbackQuery, repo: Repo, state: FSMContext):
    data = await state.get_data()
    await state.finish()

    executor = await repo.get_user_by_id(data["executor_id"])
    client = await repo.get_user_by_telegram_id(call.from_user.id)
    deal = await repo.add_deal(
        client_id=client.id,
        executor_id=data["executor_id"],
        amount=data["amount"],
        conditions=data["conditions"],
    )
    await call.bot.send_message(
        chat_id=executor.telegram_id,
        text=f"Пользователь с никнеймом <code>{client.name}</code> предлагает вам сделку. "
             "Подтвердите или отмените ее",
        parse_mode="html",
    )
    await call.bot.send_message(
        executor.telegram_id,
        TEXTS["deal_info"].format(
            id=deal.id,
            is_confirmed_by_executor="не подтверждена исполнителем",
            client_name=client.name,
            executor_name=executor.name,
            amount=deal.amount,
            conditions=deal.conditions,
            is_completed="нет",
        ),
        reply_markup=get_apply_deal_by_executor_keyboard(deal.id),
        parse_mode="html",
    )
    await call.message.answer(
        "Информация о сделке успешно сохранена и отправлена исполнителю на подтверждение. Ожидайте ответа"
    )
    await call.answer()


async def again_creating_deal(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await call.message.answer("Хорошо, начинаем процесс создания новой сделки. Отправьте никнейм исполнителя")
    await state.set_data({})
    await state.set_state(CreateDeal.here_executor_id)


async def start_deal_with_id(call: CallbackQuery, repo: Repo, state: FSMContext):
    await state.finish()
    await call.answer()

    deal_id = call.data.split("_")[-1]
    deal = await repo.update_deal(deal_id=int(deal_id), is_confirmed_by_executor=True)
    await call.message.answer(
        text=f"Сделка (id: <code>{deal.id}</code>) подтверждена. "
             "Можете начинать работу. Вы получите деньги после успешного выполнения работы",
        parse_mode="html",
    )
    client = await repo.get_user_by_id(deal.client_id)
    await repo.update_user(user_id=client.id, balance=client.balance - deal.amount * (1 + FEE))
    await call.bot.send_message(
        chat_id=client.telegram_id,
        text=f"Вашу сделку (id: <code>{deal.id}</code>) подтвердил исполнитель. Деньги списаны с вашего счета",
        parse_mode="html",
    )


async def decline_deal_with_id(call: CallbackQuery, repo: Repo, state: FSMContext):
    await state.finish()
    await call.answer()

    deal_id = call.data.split("_")[-1]
    deal = await repo.get_deal_by_id(int(deal_id))
    client = await repo.get_user_by_id(deal.client_id)
    await call.message.answer(
        f"Сделка (id: <code>{deal.id}</code>) отменена.",
        parse_mode="html",
    )
    await call.bot.send_message(
        chat_id=client.telegram_id,
        text=f"Вашу сделку (id: <code>{deal.id}</code>) отменил исполнитель.",
        parse_mode="html",
    )


async def my_deals(call: CallbackQuery, repo: Repo, state: FSMContext):
    await state.finish()
    await call.answer()

    me = await repo.get_user_by_telegram_id(call.from_user.id)
    deals = await repo.get_user_deals(me.id)
    if not me.show_completed_deals:
        deals = [deal for deal in deals if not deal.is_completed]

    await state.set_state(Rialto.swap_deals)
    paginator = Paginator(
        data=[
            [InlineKeyboardButton(
                text=f"id: {deal.id} ({'в работе' if not deal.is_completed else 'завершена'})",
                callback_data=f"deal_{deal.id}")
            ]
            for deal in deals
        ],
        dp=Dispatcher.get_current(),
        state=Rialto.swap_deals,
        size=10,
    )

    await call.message.answer(
        text="Ваши сделки:",
        reply_markup=paginator(),
    )


async def deal_callback(call: CallbackQuery, repo: Repo, state: FSMContext):
    await state.finish()
    await call.answer()

    deal_id = call.data.split("_")[-1]
    deal = await repo.get_deal_by_id(int(deal_id))
    executor = await repo.get_user_by_id(deal.executor_id)
    client = await repo.get_user_by_id(deal.client_id)
    me = await repo.get_user_by_telegram_id(call.from_user.id)

    await call.message.answer(
        TEXTS["deal_info"].format(
            id=deal.id,
            is_confirmed_by_executor=("не " if not deal.is_confirmed_by_executor else "") + "подтверждена исполнителем",
            client_name=executor.name,
            executor_name=client.name,
            amount=deal.amount,
            conditions=deal.conditions,
            is_completed="да" if deal.is_completed else "нет",
        ),
        reply_markup=get_deal_keyboard(
            deal=deal,
            is_my_deal=executor.id == me.id,
            with_user_id=deal.client_id if executor.id == me.id else deal.executor_id
        ),
        parse_mode="html",
    )


async def end_deal(call: CallbackQuery, repo: Repo, state: FSMContext):
    await state.finish()
    await call.answer()

    deal_id = int(call.data.split("_")[-1])
    deal = await repo.get_deal_by_id(deal_id)
    client = await repo.get_user_by_id(deal.client_id)
    executor = await repo.get_user_by_id(deal.executor_id)

    await call.message.answer("Запрос на подтверждение завершения сделки отправлен клиенту. Ожидайте его решения")

    await call.bot.send_message(
        chat_id=client.telegram_id,
        text="Исполнитель предлагает завершить сделку. Если условия выполнены, подтвердите завершение.\n"
             "Если нет, обратитесь в техническую поддержку для разрешения вопроса",
    )
    await call.bot.send_message(
        chat_id=client.telegram_id,
        text=TEXTS["deal_info"].format(
            id=deal.id,
            is_confirmed_by_executor=("не " if not deal.is_confirmed_by_executor else "") + "подтверждена исполнителем",
            client_name=client.name,
            executor_name=executor.name,
            amount=deal.amount,
            conditions=deal.conditions,
            is_completed="да" if deal.is_completed else "нет",
        ),
        reply_markup=get_approve_deal_keyboard(deal.id),
        parse_mode="html",
    )


async def approve_end_deal(call: CallbackQuery, repo: Repo, state: FSMContext):
    await state.finish()
    await call.answer()

    deal_id = int(call.data.split("_")[-1])
    deal = await repo.get_deal_by_id(deal_id)

    executor = await repo.get_user_by_id(deal.executor_id)
    await repo.update_deal(
        deal_id=deal_id,
        is_completed=True
    )
    await repo.update_user(
        telegram_id=executor.telegram_id,
        balance=executor.balance + deal.amount,
    )
    await call.bot.send_message(
        chat_id=executor.telegram_id,
        text=f"Клиент подтвердил завершение сделки (id <code>{deal.id}</code>)\n"
             "Деньги переведены вам на счет",
        parse_mode="html",
    )
    await call.message.answer(
        "Сделка завершена. Деньги отправлены на счет исполнителя.",
        reply_markup=get_tip_keyboard(deal.executor_id),
    )
    await call.message.answer(
        "Оцените работу исполнителя от 1 до 5, нажав кнопку ниже (1 - плохо, 5 - хорошо)",
        reply_markup=get_rating_keyboard(deal.id)
    )
    await state.set_state(Rating.here_rate)


async def rating_here_rate(call: CallbackQuery, repo: Repo, state: FSMContext):
    await call.answer()
    await state.finish()
    _, rate, deal_id = call.data.split("_")
    if not (1 <= rate <= 5):
        return
    await repo.update_deal(int(deal_id), rating=int(rate))
    await call.message.answer("Спасибо! Оценка поставлена исполнителю")


async def support_deal(call: CallbackQuery, state: FSMContext):
    await call.answer()
    await state.finish()

    await call.message.answer(
        TEXTS["support"] + "\n\nОтправьте им доказательства обмана со второй стороны, а также информацию о сделке"
    )


async def tip(call: CallbackQuery, state: FSMContext):
    executor_id = int(call.data.split("_")[-1])
    await call.answer()

    await call.message.answer("Введите сумму чаевых")
    await state.set_state(Tip.here_amount)
    await state.update_data(executor_id=executor_id)


async def tip_here_amount(message: Message, repo: Repo, state: FSMContext):
    try:
        amount = int(message.text)
    except ValueError:
        return await message.answer("Сумма должна быть числом")

    me = await repo.get_user_by_telegram_id(message.from_id)
    if me.balance < amount:
        return await message.answer("Недостаточный баланс. Отправьте другую сумму")

    data = await state.get_data()

    client = await repo.get_user_by_telegram_id(message.from_id)
    executor = await repo.get_user_by_id(data["executor_id"])
    await repo.update_user(user_id=client.id, balance=client.balance - amount)
    await repo.update_user(user_id=executor.id, balance=executor.balance + amount)

    await message.answer("Чаевые переведены исполнителю. Спасибо!")
    await message.bot.send_message(
        executor.telegram_id,
        f"Заказчик оставил вам чаевые (${amount}). Спасибо за работу!"
    )
    await state.finish()


def register_user_rialto_handlers(dp: Dispatcher):
    # биржа труда
    dp.register_message_handler(rialto, Text("Услуги💼"), state="*")
    dp.register_callback_query_handler(rialto_here_job, Text(startswith="job"), state=Rialto.here_job)
    dp.register_callback_query_handler(rialto_here_price, Text(startswith="price"), state=Rialto.here_price)

    # user info
    dp.register_callback_query_handler(user_info, Text(startswith="user"), state=Rialto.swap)

    # гарант
    dp.register_message_handler(guarantee, Text("Сделки💰"), state="*")
    dp.register_callback_query_handler(create_deal, Text("create_deal"), state="*")
    dp.register_message_handler(create_deal_here_executor_id, state=CreateDeal.here_executor_id)
    dp.register_callback_query_handler(create_deal_here_executor_id_callback, Text(startswith="create_deal_"),
                                       state=Rialto.swap)
    dp.register_message_handler(create_deal_here_amount, state=CreateDeal.here_amount)
    dp.register_message_handler(create_deal_here_conditions, state=CreateDeal.here_conditions)
    dp.register_callback_query_handler(apply_creating_deal, Text("apply_creating_deal"),
                                       state=CreateDeal.here_conditions)
    dp.register_callback_query_handler(again_creating_deal, Text("create_again"), state=CreateDeal.here_conditions)
    dp.register_callback_query_handler(start_deal_with_id, Text(startswith="apply_deal"), state="*")
    dp.register_callback_query_handler(decline_deal_with_id, Text(startswith="decline_deal"), state="*")

    dp.register_callback_query_handler(my_deals, Text("my_deals"), state="*")
    dp.register_callback_query_handler(deal_callback, Text(startswith="deal"), state="*")
    dp.register_callback_query_handler(end_deal, Text(startswith="end_deal"), state="*")
    dp.register_callback_query_handler(approve_end_deal, Text(startswith="approve_end_deal"), state="*")
    dp.register_callback_query_handler(rating_here_rate, Text(startswith="rating"), state=Rating.here_rate)
    dp.register_callback_query_handler(support_deal, Text(startswith="support_deal"), state="*")
    dp.register_callback_query_handler(tip, Text(startswith="tip"), state="*")
    dp.register_message_handler(tip_here_amount, state=Tip.here_amount)
