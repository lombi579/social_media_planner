from aiogram.fsm.state import State, StatesGroup


class PlannerStates(StatesGroup):
    choosing_platform = State()
    choosing_account = State()
    choosing_time = State()
    entering_description = State()
    entering_hashtags = State()
    confirmation = State()
