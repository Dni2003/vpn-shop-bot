from aiogram.fsm.state import State, StatesGroup

class SettingsStates(StatesGroup):
    waiting_for_min_charge = State()
    waiting_for_welcome = State()
    waiting_for_support_user = State()
    waiting_for_support_hours = State()
