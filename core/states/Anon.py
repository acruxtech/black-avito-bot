from aiogram.dispatcher.filters.state import State, StatesGroup


class Anon(StatesGroup):
    here_id = State()
    here_message = State()
