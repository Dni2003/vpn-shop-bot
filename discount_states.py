from aiogram.fsm.state import State, StatesGroup

class DiscountStates(StatesGroup):
    # ========== حالت‌های ایجاد کد تخفیف (ادمین) ==========
    waiting_for_code = State()          # مرحله ۱: دریافت کد تخفیف
    waiting_for_type = State()           # مرحله ۲: انتخاب نوع تخفیف (درصدی/مبلغ ثابت)
    waiting_for_value = State()          # مرحله ۳: دریافت مقدار تخفیف
    waiting_for_max_uses = State()       # مرحله ۴: دریافت تعداد دفعات استفاده
    waiting_for_days = State()           # مرحله ۵: دریافت روزهای اعتبار
    
    # ========== حالت اعمال تخفیف در خرید (کاربر) ==========
    waiting_for_discount_in_purchase = State()  # دریافت کد تخفیف هنگام خرید
