from aiogram.dispatcher.filters.state import State, StatesGroup


class Tip(StatesGroup):
    here_amount = State()
