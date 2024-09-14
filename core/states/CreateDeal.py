from aiogram.dispatcher.filters.state import State, StatesGroup


class CreateDeal(StatesGroup):
    here_executor_id = State()
    here_amount = State()
    here_conditions = State()
