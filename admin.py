import aiosqlite
from aiogram import types
from aiogram.types import Message, CallbackQuery
from config import config

DB_PATH = config.DATABASE_URL.replace("sqlite+aiosqlite:///", "")

# ========== بررسی ادمین ==========
async def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS

# ========== پنل اصلی ادمین (برای bot.py) ==========
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
        
        # ارسال هر درخواست به صورت یک پیام جداگانه با عکس
        for req in requests:
            request_id, user_id, amount, photo_id, created_at = req
            
            text = f"📩 درخواست #{request_id}\n"
            text += f"👤 کاربر: {user_id}\n"
            text += f"💰 مبلغ: {amount:,} تومان\n"
            text += f"📅 تاریخ: {created_at}\n"
            
            # دکمه‌های تأیید/رد برای این درخواست
            keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
                [
                    types.InlineKeyboardButton(text="✅ تأیید", callback_data=f"approve_charge_{request_id}"),
                    types.InlineKeyboardButton(text="❌ رد", callback_data=f"reject_charge_{request_id}")
                ]
            ])
            
            # ارسال عکس به همراه دکمه‌ها
            try:
                await callback.message.answer_photo(
                    photo=photo_id,
                    caption=text,
                    reply_markup=keyboard
                )
            except:
                # اگه عکس قابل ارسال نبود، فقط متن رو بفرست
                await callback.message.answer(
                    text + "\n⚠️ عکس قابل نمایش نیست.",
                    reply_markup=keyboard
                )
        
        # دکمه بازگشت به پنل ادمین
        await callback.message.answer(
            "🔙 برای بازگشت به پنل ادمین، از دکمه زیر استفاده کن:",
            reply_markup=types.InlineKeyboardMarkup(inline_keyboard=[
                [types.InlineKeyboardButton(text="🔙 بازگشت به پنل", callback_data="back_to_admin")]
            ])
        )
        
        # حذف پیام قبلی (لیست قدیمی)
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
            text += f"🆔 درخواست: {req[0]}\n"
            text += f"👤 کاربر: {req[1]}\n"
            text += f"📦 پلن: {req[2]}\n"
            text += f"📅 تاریخ: {req[3]}\n"
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
