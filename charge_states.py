from aiogram.fsm.state import State, StatesGroup

class ChargeStates(StatesGroup):
    waiting_for_amount = State()      # منتظر دریافت مبلغ
    waiting_for_receipt = State()     # منتظر دریافت عکس رسید
