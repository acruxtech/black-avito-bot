from uuid import uuid4

from aiocryptopay.exceptions import CryptoPayAPIError, CodeErrorFactory
from aiocryptopay.const import Assets
from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.types import CallbackQuery, Message

from core.states.Withdraw import Withdraw
from core.states.Refill import Refill
from core.utils.variables import crypto
from services.db.services.repository import Repo
from services.paginator import Paginator
from config import load_config
from core.states.Registration import Registration
from core.utils.functions import *
from core.utils.keyboards import *
from core.utils.constants import *

logger = logging.getLogger(__name__)
config = load_config("config.ini")


async def registration(message: Message, state: FSMContext):
    await message.answer("Начнём регистрацию.\nВы заказчик или исполнитель?",
                         reply_markup=get_user_type_keyboard())

    await state.set_state(Registration.here_user_type)


async def registration_here_user_type(message: Message, repo: Repo, state: FSMContext):
    if message.text == "Исполнитель":
        jobs = await repo.get_jobs()
        paginator = Paginator(
            data=[
                [InlineKeyboardButton(text=job.title, callback_data=f"job_{job.id}")]
                for job in jobs
            ],
            dp=Dispatcher.get_current(),
            state=Registration.here_job,
            size=10,
        )
        await message.answer(
            "Укажите свое направление",
            reply_markup=paginator(),
        )
        await state.set_state(Registration.here_job)
    elif message.text == "Заказчик":
        await repo.update_user(
            telegram_id=message.from_user.id,
            skills=None,
            price=None,
            job="",
            is_completed_registration=True,
            is_shadow_ban=True,
        )
        await message.answer("Регистрация завершена. Можете искать объявления в разделе 'Услуги'. Сменить роль на "
                             "'Исполнитель' можно позднее в разделе 'Профиль'",
                             reply_markup=get_empty_keyboard())
        await state.finish()
    else:
        await message.answer("Такого варианта нет. Попробуйте еще раз")


async def registration_here_job(call: CallbackQuery, state: FSMContext):
    await call.answer()
    job_id = call.data.split("_")[-1]
    await state.update_data(job_id=job_id)
    await call.message.answer(
        "Кратко опишите свои скиллы и условия работы",
        reply_markup=get_empty_keyboard(),
    )
    await state.set_state(Registration.here_skills)


async def registration_here_skills(message: Message, state: FSMContext):
    await state.update_data(skills=message.text)
    await message.answer(
        "И последнее. Выберите, к какой ценовой категории относятся ваши услуги.",
        reply_markup=get_price_keyboard(),
    )
    await state.set_state(Registration.here_price)


async def registration_here_price(call: CallbackQuery, repo: Repo, state: FSMContext):
    await call.answer()

    data = await state.get_data()
    price = call.data.split("_")[-1]
    job = await repo.get_job_by_id(int(data["job_id"]))

    user = await repo.update_user(
        telegram_id=call.from_user.id,
        job=job.title,
        skills=data["skills"],
        price=PRICE_MAPPER[price],
        is_completed_registration=True,
        is_shadow_ban=True,
    )

    for admin in config.tg_bot.admin_ids:
        text = "<b>Новая анкета</b>\n\n" + get_user_repr(user)
        await call.bot.send_message(
            chat_id=admin,
            text=text,
            parse_mode="html",
            reply_markup=get_apply_user(user.id),
        )

    await call.message.answer(
        text="Ваша анкета отправлена на проверку администраторам. Ожидайте решения",
        reply_markup=get_start_keyboard()
    )

    await state.finish()


async def profile(message: Message, repo: Repo, state: FSMContext):
    await state.finish()

    user = await repo.get_user_by_telegram_id(message.from_id)

    if not user or not user.is_completed_registration:
        await message.answer(
            "Пройдите регистрацию, чтобы получить доступ к разделу \"Профиль\"",
            reply_markup=get_registration_keyboard(),
        )
        return

    if user.is_shadow_ban and user.skills:
        await message.answer("Ваша анкета либо не подтверждена, либо заблокирована администратором!")
        return

    if user.job:
        text = get_user_repr(user)
    else:
        text = f"Заказчик (id: <code>{user.id}</code>)"

    await message.answer(
        text=text,
        reply_markup=get_profile_keyboard(),
        parse_mode="html",
    )


async def settings_handler(message: Message, repo: Repo, state: FSMContext):
    await state.finish()
    me = await repo.get_user_by_telegram_id(message.from_id)

    await message.answer(
        text="Настройки",
        reply_markup=get_profile_settings_keyboard(me.show_completed_deals),
    )


async def user_show_completed_deals(call: CallbackQuery, repo: Repo, state: FSMContext):
    data = await state.get_data()
    me = await repo.get_user_by_telegram_id(call.from_user.id)
    prev_val = me.show_completed_deals

    user = await repo.update_user(telegram_id=me.telegram_id, show_completed_deals=not prev_val)
    with suppress(BaseException):
        await call.message.edit_reply_markup(
            reply_markup=get_profile_settings_keyboard(not prev_val)
        )
    await call.answer("Успешно")


async def balance_handler(message: Message, repo: Repo, state: FSMContext):
    await state.finish()
    me = await repo.get_user_by_telegram_id(message.from_id)

    await message.answer(
        text=f"Ваш баланс: <code>${me.balance}</code>",
        parse_mode="html",
        reply_markup=get_balance_keyboard(),
    )


async def refill(call: CallbackQuery, state: FSMContext):
    await state.finish()

    await call.answer()
    await call.message.answer(
        text="Пополнение производится через @CryptoBot. Введите сумму для пополнения в долларах. "
             "Внимание, может взиматься дополнительная комиссия платежной системой!",
        parse_mode="html",
    )
    await state.set_state(Refill.here_amount)


async def refill_here_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text)
    except ValueError:
        await message.answer("Значение должно быть числом, попробуйте еще раз")
        return
    rates = await crypto.get_exchange_rates()
    rates = [rate for rate in rates if rate.source in Assets.values() and rate.target == 'USD']
    await message.answer(
        text='Выберите криптовалюту для оплаты',
        reply_markup=get_rates_keyboard(rates),
        parse_mode='html'
    )
    await state.set_state(Refill.here_crypto)
    await state.update_data(pay_amount=amount)


async def refill_here_crypto(call: CallbackQuery, state: FSMContext):
    await call.answer()

    curr = call.data.split('_')[-1]

    rates = await crypto.get_exchange_rates()         # get all rates
    rate = next(filter(lambda x: x.source == curr and x.target == 'USD', rates)).rate
    amount_pay_usd = (await state.get_data())["pay_amount"]
    amount_pay_crypto = amount_pay_usd / rate

    await call.message.edit_text(
        f'Количество {curr} для оплаты: {amount_pay_crypto}',
        reply_markup=get_crypto_pending_keyboard()
    )
    await state.update_data(curr=curr, amount=amount_pay_crypto, amount_usd=amount_pay_usd)
    await state.set_state(Refill.pay)


async def refill_here_pay(call: CallbackQuery, state: FSMContext):
    await call.answer()

    data = await state.get_data()

    try:
        invoice = await crypto.create_invoice(data["amount"], data["curr"])
    except CryptoPayAPIError | CodeErrorFactory as e:
        await call.message.answer("Ошибка во время создания чека.")
        await state.finish()
        return
    await call.message.edit_text(
        f"Счет для оплаты: {invoice.bot_invoice_url}",
        reply_markup=get_check_crypto_keyboard(invoice.invoice_id)
    )


async def refill_check(call: CallbackQuery, repo: Repo, state: FSMContext):
    data = await state.get_data()

    invoice_id = call.data.split('_')[-1]
    invoice = (await crypto.get_invoices(invoice_ids=invoice_id))[0]

    if invoice.status == 'paid':
        me = await repo.get_user_by_telegram_id(call.from_user.id)
        amount = data["amount_usd"]
        await repo.update_user(
            telegram_id=call.from_user.id,
            balance=me.balance + amount,
        )

        await call.message.edit_text(
            f"<b>Вы пополнили баланс на сумму <code>${amount}</code>.\n"
            f"Чек: <code>#{invoice_id}</code></b>",
            parse_mode="html",
        )
        await state.finish()
        await call.answer()
        return

    if invoice.status == 'active':
        await call.answer('Вы не оплатили счет! Оплатили и попробуйте снова')
    elif invoice.status == 'expired':
        await call.message.edit_text("<b>Время оплаты вышло. Платёж был удалён. Попробуйте еще раз</b>")
        await call.answer()


async def withdraw(call: CallbackQuery, state: FSMContext):
    await state.finish()

    await call.answer()
    await call.message.answer(
        text="Вывод производится переводом в @CryptoBot. Введите сумму для вывода в долларах. "
             "Внимание, может взиматься дополнительная комиссия платежной системой!",
        parse_mode="html",
    )
    await state.set_state(Withdraw.here_amount)


async def withdraw_here_amount(message: Message, repo: Repo, state: FSMContext):
    try:
        amount = float(message.text)
    except ValueError:
        await message.answer("Значение должно быть числом, попробуйте еще раз")
        return

    me = await repo.get_user_by_telegram_id(message.from_id)
    if amount > me.balance:
        await message.answer("Введенное значение больше баланса, попробуйте еще раз")
        return

    rates = await crypto.get_exchange_rates()
    rates = [rate for rate in rates if rate.source in Assets.values() and rate.target == 'USD']
    await message.answer(
        text='Выберите криптовалюту для вывода',
        reply_markup=get_rates_keyboard(rates),
        parse_mode='html'
    )
    await state.set_state(Withdraw.here_crypto)
    await state.update_data(withdraw_amount=amount)


async def withdraw_here_crypto(call: CallbackQuery, state: FSMContext):
    await call.answer()

    curr = call.data.split('_')[-1]

    rates = await crypto.get_exchange_rates()         # get all rates
    rate = next(filter(lambda x: x.source == curr and x.target == 'USD', rates)).rate
    amount_withdraw_usd = (await state.get_data())["withdraw_amount"]
    amount_withdraw_crypto = amount_withdraw_usd / rate

    try:
        await crypto.transfer(
            user_id=call.from_user.id,
            asset=curr,
            amount=amount_withdraw_crypto,
            spend_id=str(uuid4()),
        )
    except CodeErrorFactory as e:
        logger.error(e)
        await call.message.answer("Ошибка во время перевода средств. Попробуйте позже")
        await state.finish()
        return

    await call.message.edit_text('Деньги были отправлены вам на счет в @CryptoBot', reply_markup=None)
    await state.finish()


def register_user_profile_handlers(dp: Dispatcher):
    # регистрация
    dp.register_message_handler(registration, Text(["Начать регистрацию", "Пройти регистрацию снова"]), state="*")
    dp.register_message_handler(registration_here_user_type, state=Registration.here_user_type)
    dp.register_callback_query_handler(registration_here_job, Text(startswith="job"), state=Registration.here_job)
    dp.register_message_handler(registration_here_skills, state=Registration.here_skills)
    dp.register_callback_query_handler(registration_here_price, Text(startswith="price"), state=Registration.here_price)

    # меню
    dp.register_message_handler(profile, Text("Профиль"), state="*")
    dp.register_message_handler(balance_handler, Text("Кошелек"), state="*")
    dp.register_message_handler(settings_handler, Text("Настройки"), state="*")
    dp.register_callback_query_handler(user_show_completed_deals, Text("user_completed_deals"), state="*")

    # refill
    dp.register_callback_query_handler(refill, Text("refill"), state="*")
    dp.register_message_handler(refill_here_amount, state=Refill.here_amount)
    dp.register_callback_query_handler(refill_here_crypto, Text(startswith="сhoose_сrypto"), state=Refill.here_crypto)
    dp.register_callback_query_handler(refill_here_pay, Text(startswith="pay"), state=Refill.pay)
    dp.register_callback_query_handler(refill_check, Text(startswith="crypto_invoice"), state=Refill.pay)

    # withdraw
    dp.register_callback_query_handler(withdraw, Text("withdraw"), state="*")
    dp.register_message_handler(withdraw_here_amount, state=Withdraw.here_amount)
    dp.register_callback_query_handler(withdraw_here_crypto, Text(startswith="сhoose_сrypto"), state=Withdraw.here_crypto)
