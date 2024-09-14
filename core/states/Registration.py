from aiogram.dispatcher.filters.state import State, StatesGroup


class Registration(StatesGroup):
    here_user_type = State()
    here_job = State()
    here_skills = State()
    here_price = State()