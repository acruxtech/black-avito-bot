from aiogram.dispatcher.filters.state import State, StatesGroup


class Rialto(StatesGroup):
    here_job = State()
    here_price = State()

    swap = State()
    swap_deals = State()
