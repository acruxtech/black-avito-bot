from aiogram.dispatcher.filters.state import State, StatesGroup


class Profile(StatesGroup):
    promote = State()
    highlight = State()
