import aiosqlite
from aiogram import types
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from config import config
from datetime import datetime, timedelta

# ========== Import State classes ==========
from broadcast_states import BroadcastStates
from discount_states import DiscountStates

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
        [types.InlineKeyboardButton(text="👥 کاربران", callback_data="admin_users")],
        [types.InlineKeyboardButton(text="💰 تراکنش‌ها", callback_data="admin_transactions")],
        [types.InlineKeyboardButton(text="📊 آمار", callback_data="admin_stats")],
        [types.InlineKeyboardButton(text="➕ شارژ کاربر", callback_data="admin_add_balance")]
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
    """ذخیره فیلتر و شروع فرآیند ارسال پیام"""
    await state.update_data(filter_type=filter_type)
    await state.set_state(BroadcastStates.waiting_for_text)
    await callback.message.edit_text(
        "✍️ لطفاً متن پیام را ارسال کنید.\n"
        "می‌توانید از مارک‌داون استفاده کنید."
    )
    await callback.answer()

# ========== مدیریت تخفیف‌ها (روش ساده مرحله‌ای) ==========
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
    """مرحله ۱: دریافت کد تخفیف"""
    await state.set_state(DiscountStates.waiting_for_code)
    await callback.message.edit_text(
        "🎟 مرحله ۱ از ۵:\n\n"
        "📝 لطفاً کد تخفیف را وارد کنید:\n"
        "مثال: SUMMER10"
    )
    await callback.answer()

async def discount_process_code(message: Message, state: FSMContext):
    """مرحله ۲: دریافت نوع تخفیف"""
    code = message.text.upper().strip()
    await state.update_data(code=code)
    await state.set_state(DiscountStates.waiting_for_type)
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🔢 درصدی", callback_data="discount_type_percent")],
        [types.InlineKeyboardButton(text="💰 مبلغ ثابت", callback_data="discount_type_fixed")]
    ])
    await message.answer(
        f"🎟 مرحله ۲ از ۵:\n\n"
        f"📝 کد: {code}\n\n"
        "نوع تخفیف را انتخاب کنید:",
        reply_markup=keyboard
    )

async def discount_process_type(callback: CallbackQuery, state: FSMContext):
    """مرحله ۳: دریافت مقدار تخفیف"""
    discount_type = callback.data.split("_")[2]  # percent یا fixed
    await state.update_data(discount_type=discount_type)
    await state.set_state(DiscountStates.waiting_for_value)
    
    type_text = "درصد" if discount_type == "percent" else "تومان"
    await callback.message.edit_text(
        f"🎟 مرحله ۳ از ۵:\n\n"
        f"📝 نوع: {type_text}\n\n"
        f"💰 مقدار تخفیف را به {type_text} وارد کنید:\n"
        f"{'مثال: 10 (برای ۱۰%)' if discount_type == 'percent' else 'مثال: 50000 (برای ۵۰,۰۰۰ تومان)'}"
    )
    await callback.answer()

async def discount_process_value(message: Message, state: FSMContext):
    """مرحله ۴: دریافت تعداد استفاده"""
    try:
        value = int(message.text)
        data = await state.get_data()
        if data.get("discount_type") == "percent" and value > 100:
            await message.answer("❌ تخفیف درصدی نمی‌تواند بیشتر از ۱۰۰ باشد. لطفاً مجدداً وارد کنید.")
            return
        await state.update_data(value=value)
        await state.set_state(DiscountStates.waiting_for_max_uses)
        await message.answer(
            f"🎟 مرحله ۴ از ۵:\n\n"
            f"📝 مقدار: {value}\n\n"
            f"📌 تعداد دفعاتی که این کد قابل استفاده است را وارد کنید:\n"
            f"مثال: 5 (یعنی ۵ نفر می‌توانند استفاده کنند)"
        )
    except ValueError:
        await message.answer("❌ لطفاً یک عدد معتبر وارد کنید.")

async def discount_process_max_uses(message: Message, state: FSMContext):
    """مرحله ۵: دریافت روزهای اعتبار"""
    try:
        max_uses = int(message.text)
        await state.update_data(max_uses=max_uses)
        await state.set_state(DiscountStates.waiting_for_days)
        await message.answer(
            f"🎟 مرحله ۵ از ۵ (آخرین مرحله):\n\n"
            f"📌 تعداد استفاده: {max_uses}\n\n"
            f"📅 تعداد روزهای اعتبار کد را وارد کنید:\n"
            f"مثال: 30 (یعنی ۳۰ روز اعتبار دارد)\n"
            f"💡 عدد ۰ به معنای نامحدود است."
        )
    except ValueError:
        await message.answer("❌ لطفاً یک عدد معتبر وارد کنید.")

async def discount_process_days(message: Message, state: FSMContext):
    """مرحله نهایی: ایجاد کد تخفیف"""
    try:
        days = int(message.text)
        data = await state.get_data()
        code = data.get("code")
        discount_type = data.get("discount_type")
        value = data.get("value")
        max_uses = data.get("max_uses")
        
        expires_at = None
        if days > 0:
            expires_at = (datetime.now() + timedelta(days=days)).isoformat()
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO discount_codes (code, discount_type, discount_value, max_uses, expires_at) VALUES (?, ?, ?, ?, ?)",
                (code, discount_type, value, max_uses, expires_at)
            )
            await db.commit()
        
        type_text = "درصد" if discount_type == "percent" else "مبلغ ثابت"
        await message.answer(
            f"✅ کد تخفیف با موفقیت ایجاد شد!\n\n"
            f"🎟 کد: {code}\n"
            f"📊 نوع: {type_text}\n"
            f"💰 مقدار: {value} {'' if discount_type == 'percent' else 'تومان'}\n"
            f"📌 تعداد استفاده: {max_uses}\n"
            f"📅 انقضا: {expires_at or 'نامحدود'}"
        )
        await state.clear()
        
    except aiosqlite.IntegrityError:
        await message.answer("❌ این کد قبلاً استفاده شده است. لطفاً کد دیگری وارد کنید.")
    except ValueError:
        await message.answer("❌ لطفاً یک عدد معتبر وارد کنید.")
    except Exception as e:
        await message.answer(f"❌ خطا: {str(e)}")
        await state.clear()

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
