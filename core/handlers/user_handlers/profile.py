import json
import time
from uuid import uuid4

import requests
from aiocryptopay.exceptions import CryptoPayAPIError, CodeErrorFactory
from aiocryptopay.const import Assets
from aiogram import Dispatcher
from aiogram.dispatcher import FSMContext
from aiogram.dispatcher.filters import Text
from aiogram.types import CallbackQuery, Message
from bs4 import BeautifulSoup

from core.states.Profile import Profile
from core.states.Withdraw import Withdraw
from core.states.Refill import Refill
from core.utils.variables import crypto, lolz
from services.api.lolzapi import TooManyRequestsException
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
    if message.text == "Исполнитель🤝":
        user = await repo.get_user_by_telegram_id(message.from_id)
        with open('settings.json', 'r') as file:
            data = json.load(file)
        start_payment = data["start_payment"]
        if start_payment > 0 and (user.is_paid is False or user.is_paid is None):
            if user.balance < start_payment:
                return await message.answer("Чтобы быть исполнителем необходимо внести единоразовый платеж. Он "
                                            "списывается только один раз и нужен, чтобы удостовериться в серьезности"
                                            "ваших намерений по использованию нашей платформы."
                                            f"Зарегистрируйтесь в качестве исполнителя, "
                                            f"пополните баланс на ${data['start_payment']} и попробуйте снова")
            else:
                await message.answer(
                    "Чтобы быть исполнителем необходимо внести единоразовый платеж. Он "
                    "списывается только один раз и нужен, чтобы удостовериться в серьезности"
                    "ваших намерений по использованию нашей платформы."
                    f"С вашего баланса списано ${data['start_payment']}. Можете продолжать регистрацию"
                )
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
    elif message.text == "Заказчик🛍️":
        await repo.update_user(
            telegram_id=message.from_user.id,
            skills=None,
            price=None,
            job="",
            is_completed_registration=True,
            is_shadow_ban=True,
        )
        await message.answer("Регистрация завершена. Можете искать объявления в разделе 'Услуги💼'. Сменить роль на "
                             "'Исполнитель' можно позднее в разделе 'Профиль👤'",
                             reply_markup=get_empty_keyboard())
        await state.finish()
    else:
        await message.answer("Такого варианта нет. Попробуйте еще раз")


async def registration_here_job(call: CallbackQuery, state: FSMContext):
    await call.answer()
    job_id = call.data.split("_")[-1]
    await state.update_data(job_id=job_id)
    await call.message.answer(
        "Кратко опишите свою услугу и условия работы",
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
            "Пройдите регистрацию, чтобы получить доступ к разделу \"Профиль👤\"",
            reply_markup=get_registration_keyboard(),
        )
        return

    if user.is_shadow_ban and user.skills:
        await message.answer("Ваша анкета либо не подтверждена, либо заблокирована администратором!")
        return

    if user.job:
        deals = await repo.get_user_executor_completed_deals(user.id)
        text = get_user_repr(
            user,
            rating=get_user_rating(deals),
            summ=sum(deal.amount for deal in deals)
        )
    else:
        text = f"Заказчик (никнейм: <code>{user.name}</code>)"

    await message.answer(
        text=text,
        reply_markup=get_profile_keyboard(user.job is not None, user.is_highlight),
        parse_mode="html",
    )


async def promote_profile(message: Message, repo: Repo, state: FSMContext):
    me = await repo.get_user_by_telegram_id(message.from_id)
    competitors = await repo.get_users_where(
        job_id=int(me.job_id),
        price=me.price,
        is_shadow_ban=False,
    )
    max_priority = max(competitor.priority for competitor in competitors)
    summ = round(START_BET ** (max_priority + 1), 2)
    if summ < me.balance:
        await message.answer(
            f"Необходимо ${summ}. Списать с баланса и продвинуть анкету?",
            reply_markup=get_promote_keyboard(),
        )
        await state.set_state(Profile.promote)
        await state.update_data(summ=summ)
    else:
        return await message.answer(
            f"Необходимо ${summ}. На балансе недостаточно средств. Пополните и попробуйте еще раз",
        )


async def approve_promote_profile(call: CallbackQuery, repo: Repo, state: FSMContext):
    await call.answer()

    user = await repo.get_user_by_telegram_id(call.from_user.id)
    data = await state.get_data()
    await repo.update_user(user_id=user.id, priority=user.priority + 1, balance=user.balance - data["summ"])
    await call.message.answer("Отлично! Теперь ваша анкета лучше продвигается")
    await state.finish()


async def highlight_profile(message: Message, repo: Repo, state: FSMContext):
    me = await repo.get_user_by_telegram_id(message.from_id)
    if HIGHLIGHT_PRICE < me.balance:
        await message.answer(
            f"Необходимо ${HIGHLIGHT_PRICE}. Списать с баланса и выделить анкету?",
            reply_markup=get_highlight_keyboard(),
        )
        await state.set_state(Profile.highlight)
    else:
        return await message.answer(
            f"Необходимо ${HIGHLIGHT_PRICE}. На балансе недостаточно средств. Пополните и попробуйте еще раз",
        )


async def approve_highlight_profile(call: CallbackQuery, repo: Repo, state: FSMContext):
    await call.answer()

    user = await repo.get_user_by_telegram_id(call.from_user.id)
    data = await state.get_data()
    await repo.update_user(user_id=user.id, is_highlight=True, balance=user.balance - HIGHLIGHT_PRICE)
    await call.message.answer("Отлично! Теперь ваша анкета лучше видна")
    await state.finish()


async def settings_handler(message: Message, repo: Repo, state: FSMContext):
    await state.finish()
    me = await repo.get_user_by_telegram_id(message.from_id)

    await message.answer(
        text="Настройки⚙️",
        reply_markup=get_profile_settings_keyboard(me.show_completed_deals),
    )


async def user_show_completed_deals(call: CallbackQuery, repo: Repo):
    me = await repo.get_user_by_telegram_id(call.from_user.id)
    prev_val = me.show_completed_deals

    await repo.update_user(telegram_id=me.telegram_id, show_completed_deals=not prev_val)
    with suppress(BaseException):
        await call.message.edit_reply_markup(
            reply_markup=get_profile_settings_keyboard(not prev_val)
        )
    await call.answer("Успешно")


async def balance_handler(message: Message, repo: Repo, state: FSMContext):
    await state.finish()
    me = await repo.get_user_by_telegram_id(message.from_id)

    await message.answer(
        text=f"Ваш баланс: <code>${round(me.balance, 3)}</code>",
        parse_mode="html",
        reply_markup=get_balance_keyboard(),
    )


async def refill(call: CallbackQuery, state: FSMContext):
    await state.finish()

    await call.answer()
    await call.message.answer(
        text="Выберите способ пополнения",
        reply_markup=get_payment_methods_keyboard(),
    )
    await state.set_state(Refill.here_method)


async def refill_here_method(call: CallbackQuery, state: FSMContext):
    method = call.data.split("_")[-1]
    await state.update_data(method=method)
    if method == "cryptobot":
        await call.message.answer(
            text="Пополнение будет производиться через @CryptoBot. Введите сумму для пополнения в долларах. "
                 "Внимание, может взиматься дополнительная комиссия платежной системой!",
            parse_mode="html",
        )
    elif method == "lolz":
        res = requests.get("https://currencyapi.com/currency-conversion/usd-rub-1")
        usd_rate = None
        if res.status_code == 200:
            with suppress(BaseException):
                soup = BeautifulSoup(res.text, 'html.parser')
                divs = soup.find_all('div', class_='text-center mt-3')
                usd_rate = float(divs[1].text.strip().split()[0])
        if usd_rate is None:
            usd_rate = 100
        await state.update_data(usd_rate=usd_rate)
        await call.message.answer(
            text="Пополнение будет производиться через https://lzt.market. Введите сумму для пополнения в рублях. "
                 f"На баланс бота будут начислены доллары по курсу <b>1USD = {round(usd_rate, 2)}RUB</b>\n"
                 "Внимание, может взиматься дополнительная комиссия платежной системой!",
            parse_mode="html",
        )
    await state.set_state(Refill.here_amount)
    await call.answer()


async def refill_here_amount(message: Message, state: FSMContext):
    try:
        amount = float(message.text)
    except ValueError:
        await message.answer("Значение должно быть числом, попробуйте еще раз")
        return

    data = await state.get_data()
    if data["method"] == "cryptobot":
        rates = await crypto.get_exchange_rates()
        rates = [rate for rate in rates if rate.source in Assets.values() and rate.target == 'USD']
        await message.answer(
            text='Выберите криптовалюту для оплаты',
            reply_markup=get_rates_keyboard(rates),
            parse_mode='html'
        )
        await state.set_state(Refill.here_crypto)
        await state.update_data(pay_amount=amount)      # pay_amount - сколько начислится на баланс (в долларах)
    elif data["method"] == "lolz":
        comment = int(time.time() * 100)
        lolz_username = config.lolz.username
        url = f"https://lzt.market/balance/transfer?username={lolz_username}&amount={amount}&comment={comment}"
        await message.answer(
            f"Оплатите по кнопке, а затем подтвердите оплату\n"
            "<i>ВНИМАНИЕ! Не изменяйте комментарий и юзернейм получателя, иначе деньги не поступят на счет!</i>",
            parse_mode="html",
            reply_markup=get_lolz_keyboard(url),
        )
        await state.set_state(Refill.pay)
        await state.update_data(amount=amount, pay_amount=round(amount / data["usd_rate"], 2), comment=comment)
        return


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


async def refill_here_crypto_pay(call: CallbackQuery, state: FSMContext):
    await call.answer()

    data = await state.get_data()

    try:
        invoice = await crypto.create_invoice(data["amount"], data["curr"])
    except CryptoPayAPIError | CodeErrorFactory:
        await call.message.answer("Ошибка во время создания чека.")
        await state.finish()
        return
    await call.message.edit_text(
        f"Счет для оплаты: {invoice.bot_invoice_url}",
        reply_markup=get_check_crypto_keyboard(invoice.invoice_id)
    )


async def refill_here_lolz_pay(call: CallbackQuery, repo: Repo, state: FSMContext):
    data = await state.get_data()

    try:
        payments = lolz.market_payments(
            type_='income',
            pmin=data["amount"],
            pmax=data["amount"],
            comment=data["comment"],
        )["payments"]

    except TooManyRequestsException as e:
        await call.answer('Слишком много проверок! Подождите немного и попробуйте снова')
        return

    if not payments:
        await call.answer('Вы не оплатили счет! Оплатите и попробуйте снова')
        return

    me = await repo.get_user_by_telegram_id(call.from_user.id)
    await repo.update_user(
        telegram_id=call.from_user.id,
        balance=me.balance + data["pay_amount"],
    )

    await call.message.edit_text(
        f"<b>Вы пополнили баланс на сумму <code>${data['pay_amount']}</code>.\n"
        f"Чек: <code>#{data['comment']}</code></b>",
        parse_mode="html",
    )
    await state.finish()
    await call.answer()


async def refill_crypto_check(call: CallbackQuery, repo: Repo, state: FSMContext):
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
    dp.register_message_handler(registration, Text(["Начать регистрацию📝", "Пройти регистрацию снова🔄"]), state="*")
    dp.register_message_handler(registration_here_user_type, state=Registration.here_user_type)
    dp.register_callback_query_handler(registration_here_job, Text(startswith="job"), state=Registration.here_job)
    dp.register_message_handler(registration_here_skills, state=Registration.here_skills)
    dp.register_callback_query_handler(registration_here_price, Text(startswith="price"), state=Registration.here_price)

    # меню
    dp.register_message_handler(profile, Text("Профиль👤"), state="*")
    dp.register_message_handler(balance_handler, Text("Кошелек💳"), state="*")
    dp.register_message_handler(settings_handler, Text("Настройки⚙️"), state="*")
    dp.register_callback_query_handler(user_show_completed_deals, Text("user_completed_deals"), state="*")
    dp.register_message_handler(promote_profile, Text("Продвигать анкету📈"), state="*")
    dp.register_callback_query_handler(approve_promote_profile, Text("promote_profile"), state=Profile.promote)
    dp.register_message_handler(highlight_profile, Text("Выделить анкету✨"), state="*")
    dp.register_callback_query_handler(approve_highlight_profile, Text("highlight_profile"), state=Profile.highlight)

    # refill
    dp.register_callback_query_handler(refill, Text("refill"), state="*")
    dp.register_callback_query_handler(refill_here_method, Text(startswith="paymentmethod"), state=Refill.here_method)
    dp.register_message_handler(refill_here_amount, state=Refill.here_amount)
    dp.register_callback_query_handler(refill_here_crypto, Text(startswith="сhoose_сrypto"), state=Refill.here_crypto)
    dp.register_callback_query_handler(refill_here_crypto_pay, Text(startswith="pay"), state=Refill.pay)
    dp.register_callback_query_handler(refill_crypto_check, Text(startswith="crypto_invoice"), state=Refill.pay)
    dp.register_callback_query_handler(refill_here_lolz_pay, Text(startswith="lolz_invoice"), state=Refill.pay)

    # withdraw
    dp.register_callback_query_handler(withdraw, Text("withdraw"), state="*")
    dp.register_message_handler(withdraw_here_amount, state=Withdraw.here_amount)
    dp.register_callback_query_handler(withdraw_here_crypto, Text(startswith="сhoose_сrypto"),
                                       state=Withdraw.here_crypto)
