from aiogram.dispatcher.filters.state import State, StatesGroup


class AddJob(StatesGroup):
    here_title = State()


class ChangeJob(StatesGroup):
    here_title = State()
    here_new_title = State()


class DeleteJob(StatesGroup):
    here_title = State()


class DealSettings(StatesGroup):
    here_id = State()


class UserSettings(StatesGroup):
    here_id = State()
    here_action = State()
    here_balance_amount = State()
    here_message_text = State()


class Mailing(StatesGroup):
    here_time = State()
    forward_post = State()
    apply = State()


class CancelDeal(StatesGroup):
    here_id = State()
    here_money_solution = State()


class StartPayment(StatesGroup):
    here_amount = State()
