from aiogram.dispatcher.filters.state import State, StatesGroup


class Rating(StatesGroup):
    here_rate = State()
