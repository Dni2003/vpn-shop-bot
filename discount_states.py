from aiogram.fsm.state import State, StatesGroup

class DiscountStates(StatesGroup):
    waiting_for_code = State()          # منتظر دریافت کد
    waiting_for_type = State()           # منتظر انتخاب نوع
    waiting_for_value = State()          # منتظر دریافت مقدار
    waiting_for_max_uses = State()       # منتظر دریافت تعداد استفاده
    waiting_for_days = State()           # منتظر دریافت روزهای اعتبار
