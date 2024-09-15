from aiogram import types

from services.db.models import Deal


def get_admin_keyboard() -> types.InlineKeyboardMarkup:
    buttons = [
        types.InlineKeyboardButton(text="Настройки", callback_data="settings"),
        types.InlineKeyboardButton(text="Пользователь", callback_data="user_settings"),
        types.InlineKeyboardButton(text="Рассылка", callback_data="mailing"),
        types.InlineKeyboardButton(text="Статистика", callback_data="statistics"),
        types.InlineKeyboardButton(text="Выгруз", callback_data="export"),
    ]
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1
    keyboard.add(*buttons)
    return keyboard


def get_back_to_admin_keyboard() -> types.InlineKeyboardMarkup:
    buttons = [
        types.InlineKeyboardButton(text="Назад", callback_data="admin"),
    ]
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1
    keyboard.add(*buttons)
    return keyboard


def get_settings_keyboard() -> types.InlineKeyboardMarkup:
    buttons = [
        types.InlineKeyboardButton(text="Виды деятельности", callback_data="job_settings"),
        types.InlineKeyboardButton(text="Посмотреть сделку по id", callback_data="check_deal"),
    ]
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1
    keyboard.add(*buttons)
    return keyboard


def get_user_settings_keyboard(is_shadow_ban: bool) -> types.InlineKeyboardMarkup:
    buttons = [
        types.InlineKeyboardButton(text="Изменить баланс", callback_data="user_balance"),
        types.InlineKeyboardButton(text="Сделки", callback_data="user_deals"),
        types.InlineKeyboardButton(text="Отправить сообщение", callback_data="user_message"),
        types.InlineKeyboardButton(text=f"{'Дать' if not is_shadow_ban else 'Снять'} теневой бан",
                                   callback_data="user_ban"),
        types.InlineKeyboardButton(text="Назад", callback_data="admin"),
    ]
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1
    keyboard.add(*buttons)
    return keyboard


def get_profile_settings_keyboard(show_completed_deals: bool) -> types.InlineKeyboardMarkup:
    buttons = [
        types.InlineKeyboardButton(text=f"{'Показывать' if not show_completed_deals else 'Скрывать'} завершенные сделки",
                                   callback_data="user_completed_deals"),
    ]
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1
    keyboard.add(*buttons)
    return keyboard


def get_price_keyboard() -> types.InlineKeyboardMarkup:
    buttons = [
        types.InlineKeyboardButton(text="💲", callback_data="price_s"),
        types.InlineKeyboardButton(text="💲💲", callback_data="price_m"),
        types.InlineKeyboardButton(text="💲💲💲", callback_data="price_l"),
    ]
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1
    keyboard.add(*buttons)
    return keyboard


def get_empty_keyboard() -> types.ReplyKeyboardRemove:
    return types.ReplyKeyboardRemove()


def get_job_settings_keyboard() -> types.InlineKeyboardMarkup:
    buttons = [
        types.InlineKeyboardButton(text="Добавить деятельность", callback_data="add_job"),
        types.InlineKeyboardButton(text="Изменить деятельность", callback_data="change_job"),
        types.InlineKeyboardButton(text="Удалить деятельность", callback_data="delete_job"),
        types.InlineKeyboardButton(text="Главное меню", callback_data="admin"),
    ]
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1
    keyboard.add(*buttons)
    return keyboard


def get_registration_keyboard() -> types.ReplyKeyboardMarkup:
    keyboard = types.ReplyKeyboardMarkup()
    keyboard.resize_keyboard = True
    keyboard.row_width = 1
    keyboard.add(
        types.KeyboardButton(text="Начать регистрацию🚀"),
    )
    return keyboard


def get_start_keyboard() -> types.ReplyKeyboardMarkup:
    keyboard = types.ReplyKeyboardMarkup()
    keyboard.resize_keyboard = True
    buttons = [
        types.KeyboardButton(text="Профиль👤"),
        types.KeyboardButton(text="Услуги"),
        types.KeyboardButton(text="Сделки"),
        types.KeyboardButton(text="Поддержка"),
    ]
    keyboard.row_width = 2
    keyboard.add(*buttons)
    return keyboard


def get_profile_keyboard() -> types.ReplyKeyboardMarkup:
    keyboard = types.ReplyKeyboardMarkup()
    keyboard.resize_keyboard = True
    keyboard.row(
        types.KeyboardButton(text="Кошелек"),
        types.KeyboardButton(text="Настройки"),
    )
    keyboard.add(
        types.KeyboardButton(text="Пройти регистрацию снова"),
    )
    keyboard.add(
        types.KeyboardButton(text="⬅️Назад"),
    )
    return keyboard


def get_balance_keyboard() -> types.InlineKeyboardMarkup:
    keyboard = types.InlineKeyboardMarkup()
    buttons = [
        types.InlineKeyboardButton(text="Пополнить", callback_data="refill"),
        types.InlineKeyboardButton(text="Вывести", callback_data="withdraw"),
    ]
    keyboard.row_width = 2
    keyboard.add(*buttons)
    return keyboard


def get_user_type_keyboard() -> types.ReplyKeyboardMarkup:
    buttons = [
        types.KeyboardButton(text="Заказчик🛍️"),
        types.KeyboardButton(text="Исполнитель👩‍💼"),
    ]
    keyboard = types.ReplyKeyboardMarkup()
    keyboard.resize_keyboard = True
    keyboard.row_width = 2
    keyboard.add(*buttons)
    return keyboard


def get_stop_mailing_keyboard(mailing_id: int) -> types.InlineKeyboardMarkup:
    keyboard = types.InlineKeyboardMarkup()
    buttons = [
        types.InlineKeyboardButton(text="Остановить рассылку", callback_data=f"stop_mailing_{mailing_id}")
    ]
    keyboard.add(*buttons)
    return keyboard


def get_cancel_keyboard(callback: str, text: str = 'Отменить') -> types.InlineKeyboardMarkup:
    keyboard = types.InlineKeyboardMarkup()
    buttons = [
        types.InlineKeyboardButton(text, callback_data=f'cancel_{callback}'),
    ]
    keyboard.add(*buttons)
    return keyboard


def get_mailing_keyboard() -> types.InlineKeyboardMarkup:
    buttons = [
        types.InlineKeyboardButton(text="Создать рассылку", callback_data="create_mailing"),
        types.InlineKeyboardButton(text="Удалить рассылку", callback_data="delete_mailing"),
    ]
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(*buttons)
    return keyboard


def get_apply_mailing_keyboard() -> types.InlineKeyboardMarkup:
    buttons = [
        types.InlineKeyboardButton(text="Отменить", callback_data="cancel_mailing"),
        types.InlineKeyboardButton(text="Подтвердить", callback_data="apply_mailing"),
    ]
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(*buttons)
    return keyboard


def get_apply_user(user_id: int) -> types.InlineKeyboardMarkup:
    buttons = [
        types.InlineKeyboardButton(text="Принять", callback_data=f"new_user_apply_{user_id}"),
        types.InlineKeyboardButton(text="Отклонить", callback_data=f"new_user_decline_{user_id}"),
    ]
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 2
    keyboard.add(*buttons)
    return keyboard


def get_guarantee_keyboard() -> types.InlineKeyboardMarkup:
    buttons = [
        types.InlineKeyboardButton(text="Мои сделки", callback_data="my_deals"),
        types.InlineKeyboardButton(text="➕Создать сделку", callback_data="create_deal"),
    ]
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1
    keyboard.add(*buttons)
    return keyboard


def get_apply_deal_keyboard() -> types.InlineKeyboardMarkup:
    buttons = [
        types.InlineKeyboardButton(text="Подтвердить создание", callback_data="apply_creating_deal"),
        types.InlineKeyboardButton(text="Заполнить заново", callback_data="create_again"),
    ]
    keyboard = types.InlineKeyboardMarkup()
    keyboard.add(*buttons)
    return keyboard


def get_apply_deal_by_executor_keyboard(deal_id: int) -> types.InlineKeyboardMarkup:
    buttons = [
        types.InlineKeyboardButton(text="Подтвердить начало работы", callback_data=f"apply_deal_{deal_id}"),
        types.InlineKeyboardButton(text="Отклонить", callback_data=f"decline_deal_{deal_id}"),
    ]
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1
    keyboard.add(*buttons)
    return keyboard


def get_deals_keyboard(deals: list[Deal]) -> types.InlineKeyboardMarkup:
    buttons = [
        types.InlineKeyboardButton(text=f"id: {deal.id} ({'в работе' if not deal.is_completed else 'завершена'})",
                                   callback_data=f"deal_{deal.id}")
        for deal in deals
    ]
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1
    keyboard.add(*buttons)
    return keyboard


def get_deal_keyboard(deal: Deal, is_my_deal: bool, with_user_id: int) -> types.InlineKeyboardMarkup | None:
    if deal.is_completed:
        return

    buttons = []
    if is_my_deal:
        buttons.append(types.InlineKeyboardButton(text="Завершить сделку", callback_data=f"end_deal_{deal.id}"))
    buttons.append(types.InlineKeyboardButton(text="Написать второй стороне", callback_data=f"anon_{with_user_id}"))
    buttons.append(types.InlineKeyboardButton(text="Обратиться в поддержку", callback_data="support_deal"))
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1
    keyboard.add(*buttons)
    return keyboard


def get_approve_deal_keyboard(deal_id: int) -> types.InlineKeyboardMarkup:
    buttons = [
        types.InlineKeyboardButton(text="Завершить сделку", callback_data=f"approve_end_deal_{deal_id}"),
        types.InlineKeyboardButton(text="Обратиться в поддержку", callback_data=f"support_deal_{deal_id}")
    ]
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1
    keyboard.add(*buttons)
    return keyboard


def get_rates_keyboard(rates) -> types.InlineKeyboardMarkup:
    keyboard = types.InlineKeyboardMarkup()
    buttons = [
        types.InlineKeyboardButton(rate.source, callback_data=f'сhoose_сrypto_{rate.source}') for rate in rates
    ]
    keyboard.add(*buttons)
    return keyboard


def get_start_chat_keyboard(with_id: int) -> types.InlineKeyboardMarkup:
    keyboard = types.InlineKeyboardMarkup()
    buttons = [
        types.InlineKeyboardButton("Перейти в чат", callback_data=f'start_chat_{with_id}')
    ]
    keyboard.add(*buttons)
    return keyboard


def get_crypto_pending_keyboard() -> types.InlineKeyboardMarkup:
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row = 1
    buttons = [
        types.InlineKeyboardButton('Получить счет', callback_data='pay'),
    ]
    keyboard.add(*buttons)
    return keyboard


def get_check_crypto_keyboard(invoice_id) -> types.InlineKeyboardMarkup:
    keyboard = types.InlineKeyboardMarkup()
    buttons = [
        types.InlineKeyboardButton("Нажмите после оплаты", callback_data=f"crypto_invoice_{invoice_id}"),
    ]
    keyboard.add(*buttons)

    return keyboard


def get_tip_keyboard(executor_id: int) -> types.InlineKeyboardMarkup:
    buttons = [
        types.InlineKeyboardButton(text="Оставить на чай", callback_data=f"tip_{executor_id}"),
    ]
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1
    keyboard.add(*buttons)
    return keyboard


def get_rating_keyboard(deal_id: int) -> types.InlineKeyboardMarkup:
    buttons = [
        types.InlineKeyboardButton(text=str(i), callback_data=f"rating_{i}_{deal_id}")
        for i in range(1, 6)
    ]
    keyboard = types.InlineKeyboardMarkup()
    keyboard.row_width = 1
    keyboard.add(*buttons)
    return keyboard


def get_scroll_keyboard(
        back: str = "",
        additional_button: types.InlineKeyboardButton = None,
        forward: str = ""
    ) -> types.InlineKeyboardMarkup:
    keyboard = types.InlineKeyboardMarkup()
    buttons = []
    if back:
        buttons.append(types.InlineKeyboardButton(text="Назад", callback_data=back))
    if additional_button:
        buttons.append(additional_button)
    if forward:
        buttons.append(types.InlineKeyboardButton(text="Далее", callback_data=forward))
    keyboard.add(*buttons)
    return keyboard
