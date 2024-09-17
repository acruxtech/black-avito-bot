from aiogram.dispatcher.filters.state import State, StatesGroup


class Refill(StatesGroup):
    here_method = State()
    here_amount = State()
    here_crypto = State()
    pay = State()
