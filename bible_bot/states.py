from aiogram.fsm.state import State, StatesGroup


class ScheduleInput(StatesGroup):
    custom_time = State()
    custom_timezone = State()
