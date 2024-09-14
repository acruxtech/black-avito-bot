from aiogram.dispatcher.filters.state import State, StatesGroup


class Refill(StatesGroup):
    here_amount = State()
    here_crypto = State()
    pay = State()
