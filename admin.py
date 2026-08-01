import aiosqlite
from aiogram import types
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from config import config
from datetime import datetime, timedelta

DB_PATH = config.DATABASE_URL.replace("sqlite+aiosqlite:///", "")

# ========== تابع تبدیل زمان به ایران ==========
def to_tehran_time(utc_str: str) -> str:
    try:
        utc_time = datetime.fromisoformat(utc_str)
        tehran_time = utc_time + timedelta(hours=3, minutes=30)
        return tehran_time.strftime("%H:%M:%S %Y-%m-%d")
    except:
        return utc_str

# ========== بررسی ادمین ==========
async def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS

# ========== پنل اصلی ادمین ==========
async def admin_panel(message: Message):
    user_id = message.from_user.id
    if not await is_admin(user_id):
        await message.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="👥 مدیریت کاربران", callback_data="admin_users")],
        [types.InlineKeyboardButton(text="📊 آمار فروش", callback_data="admin_stats")],
        [types.InlineKeyboardButton(text="💰 مدیریت تراکنش‌ها", callback_data="admin_transactions")],
        [types.InlineKeyboardButton(text="➕ شارژ کاربر", callback_data="admin_add_balance")],
        [types.InlineKeyboardButton(text="📩 درخواست‌های شارژ", callback_data="admin_charge_requests")],
        [types.InlineKeyboardButton(text="📩 درخواست‌های سرویس", callback_data="admin_service_requests")],
        [types.InlineKeyboardButton(text="📨 ارسال پیام گروهی", callback_data="admin_broadcast")],
        [types.InlineKeyboardButton(text="🎟 مدیریت تخفیف‌ها", callback_data="admin_discounts")],
        [types.InlineKeyboardButton(text="⚙️ تنظیمات", callback_data="admin_settings")]
    ])
    await message.answer("👋 به پنل مدیریت خوش اومدی!", reply_markup=keyboard)

# ========== لیست کاربران ==========
async def admin_users(callback: CallbackQuery):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT id, username, first_name, balance FROM users LIMIT 10")
            users = await cursor.fetchall()
        
        if not users:
            text = "👥 هیچ کاربری در دیتابیس ثبت نشده است."
        else:
            text = "👥 لیست کاربران (۱۰ نفر آخر):\n\n"
            for user in users:
                text += f"🆔 {user[0]} | {user[1] or 'بدون نام کاربری'} | موجودی: {user[3]} تومان\n"
        
        await callback.message.edit_text(text)
        await callback.answer()
    except Exception as e:
        await callback.message.edit_text(f"❌ خطا در دریافت کاربران:\n{str(e)}")
        await callback.answer()

# ========== آمار ==========
async def admin_stats(callback: CallbackQuery):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT COUNT(*) FROM users")
            total_users = (await cursor.fetchone())[0] or 0
            
            cursor = await db.execute("SELECT SUM(amount) FROM transactions WHERE type='deposit' AND status='completed'")
            total_revenue = (await cursor.fetchone())[0] or 0
        
        text = f"📊 آمار کلی:\n\n"
        text += f"👥 کل کاربران: {total_users}\n"
        text += f"💰 کل فروش: {total_revenue:,} تومان"
        
        await callback.message.edit_text(text)
        await callback.answer()
    except Exception as e:
        await callback.message.edit_text(f"❌ خطا در دریافت آمار:\n{str(e)}")
        await callback.answer()

# ========== شارژ کاربر (راهنما) ==========
async def admin_add_balance(callback: CallbackQuery):
    await callback.message.edit_text(
        "💰 لطفاً آیدی کاربر و مبلغ شارژ رو وارد کن:\n"
        "مثال: /add_balance 123456789 50000"
    )
    await callback.answer()

# ========== لیست درخواست‌های شارژ ==========
async def admin_charge_requests(callback: CallbackQuery):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT id, user_id, amount, receipt_photo_id, created_at FROM charge_requests WHERE status = 'pending' ORDER BY created_at DESC"
            )
            requests = await cursor.fetchall()
        
        if not requests:
            await callback.message.edit_text("📭 هیچ درخواست شارژ جدیدی وجود ندارد.")
            await callback.answer()
            return
        
        for req in requests:
            request_id, user_id, amount, photo_id, created_at = req
            local_time = to_tehran_time(created_at)
            
            text = f"📩 درخواست #{request_id}\n"
            text += f"👤 کاربر: {user_id}\n"
            text += f"💰 مبلغ: {amount:,} تومان\n"
            text += f"🕒 زمان (ایران): {local_time}\n"
            
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [
                    types.InlineKeyboardButton(text="✅ تأیید", callback_data=f"approve_charge_{request_id}"),
                    types.InlineKeyboardButton(text="❌ رد", callback_data=f"reject_charge_{request_id}")
                ]
            ])
            
            try:
                await callback.message.answer_photo(
                    photo=photo_id,
                    caption=text,
                    reply_markup=keyboard
                )
            except:
                await callback.message.answer(
                    text + "\n⚠️ عکس قابل نمایش نیست.",
                    reply_markup=keyboard
                )
        
        await callback.message.answer(
            "🔙 برای بازگشت به پنل ادمین، از دکمه زیر استفاده کن:",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="🔙 بازگشت به پنل", callback_data="back_to_admin")]
            ])
        )
        
        await callback.message.delete()
        await callback.answer()
        
    except Exception as e:
        await callback.message.edit_text(f"❌ خطا: {str(e)}")
        await callback.answer()

# ========== لیست درخواست‌های سرویس ==========
async def admin_service_requests(callback: CallbackQuery):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT id, user_id, plan_name, created_at FROM service_requests WHERE status = 'pending' ORDER BY created_at DESC"
            )
            requests = await cursor.fetchall()
        
        if not requests:
            await callback.message.edit_text("📭 هیچ درخواست سرویس جدیدی وجود ندارد.")
            await callback.answer()
            return
        
        text = "📋 لیست درخواست‌های سرویس:\n\n"
        for req in requests:
            request_id, user_id, plan_name, created_at = req
            local_time = to_tehran_time(created_at)
            text += f"🆔 درخواست: {request_id}\n"
            text += f"👤 کاربر: {user_id}\n"
            text += f"📦 پلن: {plan_name}\n"
            text += f"🕒 زمان (ایران): {local_time}\n"
            text += "─" * 20 + "\n"
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[])
        for req in requests:
            request_id = req[0]
            user_id = req[1]
            keyboard.inline_keyboard.append([
                types.InlineKeyboardButton(
                    text=f"📤 ارسال کانفیگ برای {user_id}",
                    callback_data=f"send_config_{request_id}"
                )
            ])
        keyboard.inline_keyboard.append([
            types.InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_admin")
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
    except Exception as e:
        await callback.message.edit_text(f"❌ خطا: {str(e)}")
        await callback.answer()

# ========== مدیریت تراکنش‌ها ==========
async def admin_transactions(callback: CallbackQuery):
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="📋 همه تراکنش‌ها", callback_data="trans_all")],
        [types.InlineKeyboardButton(text="💳 تراکنش‌های شارژ", callback_data="trans_deposit")],
        [types.InlineKeyboardButton(text="🛒 تراکنش‌های خرید", callback_data="trans_purchase")],
        [types.InlineKeyboardButton(text="🔍 جستجوی کاربر", callback_data="trans_search_user")],
        [types.InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_admin")]
    ])
    await callback.message.edit_text("💰 مدیریت تراکنش‌ها:\n\nیک گزینه را انتخاب کنید:", reply_markup=keyboard)
    await callback.answer()

async def show_transactions(callback: CallbackQuery, trans_type: str = None, user_id: int = None):
    try:
        query = "SELECT id, user_id, amount, type, description, status, created_at FROM transactions"
        params = []
        conditions = []
        
        if trans_type:
            conditions.append("type = ?")
            params.append(trans_type)
        if user_id:
            conditions.append("user_id = ?")
            params.append(user_id)
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY created_at DESC LIMIT 20"
        
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(query, params)
            transactions = await cursor.fetchall()
        
        if not transactions:
            await callback.message.edit_text("📭 هیچ تراکنشی یافت نشد.")
            await callback.answer()
            return
        
        text = "📋 لیست تراکنش‌ها (۲۰ مورد آخر):\n\n"
        for trans in transactions:
            trans_id, user_id, amount, trans_type, desc, status, created_at = trans
            local_time = to_tehran_time(created_at)
            
            type_emoji = "💳" if trans_type == "deposit" else "🛒"
            status_emoji = "✅" if status == "completed" else "⏳" if status == "pending" else "❌"
            
            text += f"{type_emoji} #{trans_id} | کاربر {user_id}\n"
            text += f"   💰 {amount:,} تومان | {desc or '-'}\n"
            text += f"   {status_emoji} {status} | 🕒 {local_time}\n"
            text += "─" * 20 + "\n"
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_transactions")]
        ])
        
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        await callback.message.edit_text(f"❌ خطا: {str(e)}")
        await callback.answer()

async def trans_search_user(callback: CallbackQuery):
    await callback.message.edit_text(
        "🔍 لطفاً آیدی کاربر را وارد کنید:\n"
        "مثال: /search_trans 123456789"
    )
    await callback.answer()

# ========== ارسال پیام گروهی ==========
async def admin_broadcast(callback: CallbackQuery, state: FSMContext):
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="📨 ارسال به همه کاربران", callback_data="broadcast_all")],
        [types.InlineKeyboardButton(text="👥 ارسال به کاربران فعال", callback_data="broadcast_active")],
        [types.InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_admin")]
    ])
    await callback.message.edit_text(
        "📨 ارسال پیام گروهی:\n\n"
        "لطفاً نوع ارسال را انتخاب کنید:",
        reply_markup=keyboard
    )
    await callback.answer()

async def broadcast_to_users(callback: CallbackQuery, state: FSMContext, filter_type: str):
    await state.update_data(filter_type=filter_type)
    from broadcast_states import BroadcastStates
    await state.set_state(BroadcastStates.waiting_for_text)
    await callback.message.edit_text(
        "✍️ لطفاً متن پیام را ارسال کنید.\n"
        "می‌توانید از مارک‌داون استفاده کنید."
    )
    await callback.answer()

# ========== مدیریت تخفیف‌ها (روش ساده) ==========
async def admin_discounts(callback: CallbackQuery):
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="➕ ایجاد کد تخفیف جدید", callback_data="discount_create_simple")],
        [types.InlineKeyboardButton(text="📋 لیست کدهای تخفیف", callback_data="discount_list")],
        [types.InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_admin")]
    ])
    await callback.message.edit_text(
        "🎟 مدیریت تخفیف‌ها:\n\n"
        "یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=keyboard
    )
    await callback.answer()

async def discount_create_simple(callback: CallbackQuery, state: FSMContext):
    from discount_states import DiscountStates
    await state.set_state(DiscountStates.waiting_for_code)
    await callback.message.edit_text(
        "🎟 مرحله ۱ از ۵:\n\n"
        "📝 لطفاً کد تخفیف را وارد کنید:\n"
        "مثال: SUMMER10"
    )
    await callback.answer()

async def discount_list(callback: CallbackQuery):
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT id, code, discount_type, discount_value, max_uses, used_count, expires_at, is_active FROM discount_codes ORDER BY created_at DESC"
            )
            discounts = await cursor.fetchall()
        
        if not discounts:
            await callback.message.edit_text("📭 هیچ کد تخفیفی وجود ندارد.")
            await callback.answer()
            return
        
        text = "🎟 لیست کدهای تخفیف:\n\n"
        for d in discounts:
            disc_id, code, d_type, d_value, max_uses, used_count, expires_at, is_active = d
            status = "✅ فعال" if is_active else "❌ غیرفعال"
            type_text = "درصد" if d_type == "percent" else "مبلغ ثابت"
            text += f"🆔 #{disc_id} | {code}\n"
            text += f"   {type_text}: {d_value} | {status}\n"
            text += f"   استفاده: {used_count}/{max_uses}\n"
            text += f"   انقضا: {expires_at or 'نامحدود'}\n"
            text += "─" * 20 + "\n"
        
        keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
            [types.InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_discounts")]
        ])
        await callback.message.edit_text(text, reply_markup=keyboard)
        await callback.answer()
        
    except Exception as e:
        await callback.message.edit_text(f"❌ خطا: {str(e)}")
        await callback.answer()

# ========== تنظیمات ربات ==========
async def admin_settings(callback: CallbackQuery):
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="📝 ویرایش پیام خوش‌آمدگویی", callback_data="settings_welcome")],
        [types.InlineKeyboardButton(text="💳 حداقل مبلغ شارژ", callback_data="settings_min_charge")],
        [types.InlineKeyboardButton(text="📞 اطلاعات پشتیبانی", callback_data="settings_support")],
        [types.InlineKeyboardButton(text="📦 مدیریت تعرفه‌ها", callback_data="settings_plans")],
        [types.InlineKeyboardButton(text="📊 مشاهده تنظیمات فعلی", callback_data="settings_view")],
        [types.InlineKeyboardButton(text="🔙 بازگشت", callback_data="back_to_admin")]
    ])
    await callback.message.edit_text(
        "⚙️ تنظیمات ربات:\n\n"
        "یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=keyboard
    )
    await callback.answer()

async def settings_view(callback: CallbackQuery):
    """نمایش تنظیمات فعلی"""
    from settings_manager import get_all_settings
    settings = await get_all_settings()
    
    text = "📋 تنظیمات فعلی ربات:\n\n"
    text += f"💰 حداقل مبلغ شارژ: {settings.get('min_charge_amount', 'تعیین نشده')} تومان\n"
    text += f"📞 ادمین پشتیبانی: @{settings.get('support_username', 'تعیین نشده')}\n"
    text += f"⏰ ساعت پشتیبانی: {settings.get('support_hours', 'تعیین نشده')}\n"
    text += f"📦 تعرفه‌ها: {settings.get('plans', 'تعیین نشده')}\n"
    text += f"📊 حجم‌ها: {settings.get('plan_volumes', 'تعیین نشده')}\n"
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_settings")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()

async def settings_min_charge(callback: CallbackQuery):
    """تغییر حداقل مبلغ شارژ"""
    await callback.message.edit_text(
        "💰 تغییر حداقل مبلغ شارژ:\n\n"
        "لطفاً مبلغ جدید را به تومان وارد کنید:\n"
        "مثال: 50000\n\n"
        "💡 برای انصراف، /cancel را وارد کنید."
    )
    await callback.answer()

async def settings_welcome(callback: CallbackQuery):
    """تغییر پیام خوش‌آمدگویی"""
    await callback.message.edit_text(
        "📝 تغییر پیام خوش‌آمدگویی:\n\n"
        "لطفاً متن جدید را وارد کنید.\n"
        "می‌توانید از {first_name} برای نمایش نام کاربر استفاده کنید.\n\n"
        "💡 برای انصراف، /cancel را وارد کنید."
    )
    await callback.answer()

async def settings_support(callback: CallbackQuery):
    """تغییر اطلاعات پشتیبانی"""
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🆔 تغییر ادمین", callback_data="settings_support_user")],
        [types.InlineKeyboardButton(text="⏰ تغییر ساعت پشتیبانی", callback_data="settings_support_hours")],
        [types.InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_settings")]
    ])
    await callback.message.edit_text(
        "📞 تنظیمات پشتیبانی:\n\n"
        "یکی از گزینه‌های زیر را انتخاب کنید:",
        reply_markup=keyboard
    )
    await callback.answer()

async def settings_plans(callback: CallbackQuery):
    """مدیریت تعرفه‌ها"""
    from settings_manager import get_setting
    plans = await get_setting("plans")
    volumes = await get_setting("plan_volumes")
    
    plans_list = plans.split(",") if plans else []
    volumes_list = volumes.split(",") if volumes else []
    
    text = "📦 مدیریت تعرفه‌ها:\n\n"
    if plans_list and volumes_list:
        for i, (p, v) in enumerate(zip(plans_list, volumes_list), 1):
            text += f"{i}. {int(p):,} تومان - {v}GB\n"
    else:
        text += "هیچ تعرفه‌ای تنظیم نشده است.\n"
    
    text += "\nبرای تغییر، یکی از گزینه‌های زیر را انتخاب کنید:"
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="➕ اضافه کردن تعرفه جدید", callback_data="settings_plan_add")],
        [types.InlineKeyboardButton(text="✏️ ویرایش تعرفه", callback_data="settings_plan_edit")],
        [types.InlineKeyboardButton(text="🗑 حذف تعرفه", callback_data="settings_plan_delete")],
        [types.InlineKeyboardButton(text="🔙 بازگشت", callback_data="admin_settings")]
    ])
    await callback.message.edit_text(text, reply_markup=keyboard)
    await callback.answer()
