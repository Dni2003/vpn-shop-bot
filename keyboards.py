from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton

# ========== کیبورد شیشه‌ای (دکمه‌های اصلی) ==========
def main_menu_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="🛒 خرید اشتراک"),
                KeyboardButton(text="💰 کیف پول"),
            ],
            [
                KeyboardButton(text="📞 پشتیبانی"),
                KeyboardButton(text="ℹ️ راهنما"),
            ]
        ],
        resize_keyboard=True,  # اندازه دکمه‌ها رو با صفحه هماهنگ کن
        one_time_keyboard=False  # بعد از انتخاب، کیبورد بسته نشه
    )
    return keyboard

# ========== کیبورد پلن‌های خرید (دکمه‌های اینلاین) ==========
def buy_plans_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="🌟 ۱ ماهه - ۱۰۰,۰۰۰ تومان", callback_data="buy_1month"),
            InlineKeyboardButton(text="⭐️ ۳ ماهه - ۲۵۰,۰۰۰ تومان", callback_data="buy_3month"),
        ],
        [
            InlineKeyboardButton(text="✨ ۶ ماهه - ۴۵۰,۰۰۰ تومان", callback_data="buy_6month"),
            InlineKeyboardButton(text="💎 ۱ ساله - ۷۵۰,۰۰۰ تومان", callback_data="buy_12month"),
        ],
        [
            InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_main"),
        ]
    ])
    return keyboard

# ========== کیبورد پنل ادمین ==========
def admin_panel_keyboard():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="👥 مدیریت کاربران", callback_data="admin_users"),
            InlineKeyboardButton(text="📊 آمار فروش", callback_data="admin_stats"),
        ],
        [
            InlineKeyboardButton(text="💰 مدیریت تراکنش‌ها", callback_data="admin_transactions"),
            InlineKeyboardButton(text="➕ شارژ کاربر", callback_data="admin_add_balance"),
        ],
        [
            InlineKeyboardButton(text="⚙️ تنظیمات", callback_data="admin_settings"),
        ]
    ])
    return keyboard

# ========== کیبورد تأیید خرید ==========
def confirm_purchase_keyboard(plan_name, price):
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text=f"✅ تأیید خرید {plan_name}", callback_data=f"confirm_{plan_name}"),
            InlineKeyboardButton(text="❌ انصراف", callback_data="cancel_purchase"),
        ]
    ])
    return keyboard
