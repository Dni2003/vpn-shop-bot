from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ========== منوی اصلی (دکمه‌های شیشه‌ای) ==========
def main_menu_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🛒 خرید اشتراک"), KeyboardButton(text="💰 کیف پول")],
            [KeyboardButton(text="💳 افزایش موجودی"), KeyboardButton(text="📞 پشتیبانی")],
            [KeyboardButton(text="📩 درخواست سرویس"), KeyboardButton(text="ℹ️ راهنما")]
        ],
        resize_keyboard=True
    )

# ========== سطح اول: انتخاب مدت (فقط ۱ ماهه) ==========
def buy_main_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📅 ۱ ماهه", callback_data="select_duration_1m")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main")]
    ])
    return keyboard

# ========== سطح دوم: انتخاب تعداد کاربر (فقط ۱ کاربره) ==========
def buy_user_count_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="👤 ۱ کاربره", callback_data="select_user_1")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_duration")]
    ])
    return keyboard

# ========== سطح سوم: لیست تعرفه‌ها ==========
def buy_plans_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📦 ۱۵۰,۰۰۰ تومان (۲۰GB)", callback_data="buy_1m_150k_20gb")],
        [InlineKeyboardButton(text="📦 ۲۳۹,۰۰۰ تومان (۲۸GB)", callback_data="buy_1m_239k_28gb")],
        [InlineKeyboardButton(text="📦 ۳۰۰,۰۰۰ تومان (۵۰GB)", callback_data="buy_1m_300k_50gb")],
        [InlineKeyboardButton(text="📦 ۳۳۹,۰۰۰ تومان (۵۳GB)", callback_data="buy_1m_339k_53gb")],
        [InlineKeyboardButton(text="📦 ۴۲۵,۰۰۰ تومان (۷۵GB)", callback_data="buy_1m_425k_75gb")],
        [InlineKeyboardButton(text="📦 ۵۴۰,۰۰۰ تومان (۹۰GB)", callback_data="buy_1m_540k_90gb")],
        [InlineKeyboardButton(text="📦 ۵۵۰,۰۰۰ تومان (۱۰۰GB)", callback_data="buy_1m_550k_100gb")],
        [InlineKeyboardButton(text="📦 ۸۴۰,۰۰۰ تومان (۲۱۳GB)", callback_data="buy_1m_840k_213gb")],
        [InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_user_count")]
    ])
    return keyboard

# ========== کیبورد پنل ادمین ==========
def admin_panel_keyboard():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👥 مدیریت کاربران", callback_data="admin_users"),
            InlineKeyboardButton(text="📊 آمار فروش", callback_data="admin_stats")
        ],
        [
            InlineKeyboardButton(text="💰 مدیریت تراکنش‌ها", callback_data="admin_transactions"),
            InlineKeyboardButton(text="➕ شارژ کاربر", callback_data="admin_add_balance")
        ],
        [
            InlineKeyboardButton(text="📩 درخواست‌های شارژ", callback_data="admin_charge_requests"),
            InlineKeyboardButton(text="📩 درخواست‌های سرویس", callback_data="admin_service_requests")
        ],
        [
            InlineKeyboardButton(text="⚙️ تنظیمات", callback_data="admin_settings")
        ]
    ])
