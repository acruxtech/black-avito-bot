from aiogram.dispatcher.filters.state import State, StatesGroup


class Withdraw(StatesGroup):
    here_amount = State()
    here_crypto = State()
    withdraw = State()