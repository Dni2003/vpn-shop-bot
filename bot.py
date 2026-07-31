import asyncio
import logging
import sys
import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

from config import config
from database import init_db
from admin import is_admin
from keyboards import (
    main_menu_keyboard,
    buy_main_keyboard,
    buy_user_count_keyboard,
    buy_plans_keyboard,
    admin_panel_keyboard
)
from charge_states import ChargeStates

# ========== تنظیمات اولیه ==========
logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

DB_PATH = config.DATABASE_URL.replace("sqlite+aiosqlite:///", "")

# ========== توابع کمکی ==========
async def notify_admin(user_id: int, amount: int):
    """ارسال نوتیفیکیشن به ادمین برای درخواست شارژ جدید"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT username, first_name FROM users WHERE id = ?", (user_id,))
        user = await cursor.fetchone()
    
    username = user[0] if user else "بدون نام کاربری"
    first_name = user[1] if user else "کاربر"
    
    text = f"📩 درخواست شارژ جدید:\n\n"
    text += f"👤 کاربر: {first_name} (@{username})\n"
    text += f"🆔 آیدی: {user_id}\n"
    text += f"💰 مبلغ: {amount:,} تومان\n\n"
    text += "برای تأیید یا رد، از پنل ادمین استفاده کن."
    
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text)
        except:
            pass

async def notify_admin_service(user_id: int, plan_name: str, price: int, volume: str):
    """ارسال نوتیفیکیشن درخواست سرویس جدید به ادمین"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT username, first_name FROM users WHERE id = ?", (user_id,))
        user = await cursor.fetchone()
    
    username = user[0] if user else "بدون نام کاربری"
    first_name = user[1] if user else "کاربر"
    
    text = f"📩 درخواست سرویس جدید:\n\n"
    text += f"👤 کاربر: {first_name} (@{username})\n"
    text += f"🆔 آیدی: {user_id}\n"
    text += f"📦 پلن: {plan_name}\n"
    text += f"📊 حجم: {volume}\n"
    text += f"💰 قیمت: {price:,} تومان\n\n"
    text += "برای ارسال کانفیگ، از پنل ادمین استفاده کن."
    
    for admin_id in config.ADMIN_IDS:
        try:
            await bot.send_message(admin_id, text)
        except:
            pass

# ========== دستورات عمومی ==========
@dp.message(Command("start"))
async def start_command(message: Message):
    user = message.from_user
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (id, username, first_name, last_name) VALUES (?, ?, ?, ?)",
            (user.id, user.username, user.first_name, user.last_name)
        )
        await db.commit()
    
    await message.answer(
        f"👋 سلام {user.first_name}!\n"
        "به ربات فروش VPN خوش اومدی! 🌟\n\n"
        "از دکمه‌های زیر استفاده کن:",
        reply_markup=main_menu_keyboard()
    )

@dp.message(Command("help"))
async def help_command(message: Message):
    await message.answer(
        "🤖 راهنمای ربات:\n\n"
        "1️⃣ برای خرید اشتراک از /buy استفاده کن.\n"
        "2️⃣ موجودی خودت رو با /balance ببین.\n"
        "3️⃣ برای شارژ کیف پول از /charge استفاده کن.\n"
        "4️⃣ اگه سوالی داری /support بزن.\n\n"
        "💡 در حال توسعه! امکانات بیشتر به زودی..."
    )

@dp.message(Command("buy"))
async def buy_command(message: Message):
    await message.answer(
        "📅 مدت اشتراک خود را انتخاب کنید:",
        reply_markup=buy_main_keyboard()
    )

@dp.message(Command("balance"))
async def balance_command(message: Message):
    user_id = message.from_user.id
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
        result = await cursor.fetchone()
        balance = result[0] if result else 0
    
    await message.answer(
        f"💰 موجودی کیف پول شما:\n"
        f"{balance:,} تومان\n\n"
        "💳 برای شارژ کیف پول از دکمه زیر استفاده کن."
    )

@dp.message(Command("support"))
async def support_command(message: Message):
    await message.answer(
        "📞 پشتیبانی:\n\n"
        "برای ارتباط با ادمین، از لینک زیر استفاده کن:\n"
        "@Dni2003\n\n"
        "⏰ پاسخگویی: ۹ صبح تا ۱۲ شب"
    )

@dp.message(Command("charge"))
async def charge_command(message: Message, state: FSMContext):
    await state.set_state(ChargeStates.waiting_for_amount)
    await message.answer(
        "💳 لطفاً مبلغ شارژ خود را به تومان وارد کنید:\n"
        "مثلاً: 100000\n\n"
        "🔹 حداقل مبلغ: ۱۰۰,۰۰۰ تومان"
    )

@dp.message(Command("send"))
async def send_config_to_user(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ شما دسترسی ندارید.")
        return
    
    args = message.text.split()
    if len(args) < 3:
        await message.answer(
            "❌ فرمت صحیح:\n"
            "/send [user_id] [متن کانفیگ]"
        )
        return
    
    try:
        user_id = int(args[1])
        config_text = " ".join(args[2:])
        
        await bot.send_message(
            user_id,
            f"🔐 کانفیگ سرویس شما:\n\n"
            f"`{config_text}`\n\n"
            f"✅ لطفاً این کانفیگ رو در کلاینت خود وارد کن."
        )
        
        # به‌روزرسانی وضعیت درخواست در دیتابیس
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE service_requests SET status = 'sent' WHERE user_id = ? AND status = 'pending'",
                (user_id,)
            )
            await db.commit()
        
        await message.answer(f"✅ کانفیگ به کاربر {user_id} ارسال شد.")
        
    except Exception as e:
        await message.answer(f"❌ خطا در ارسال کانفیگ: {str(e)}")

# ========== مدیریت دکمه‌های شیشه‌ای (ReplyKeyboard) ==========
@dp.message(lambda message: message.text == "🛒 خرید اشتراک")
async def handle_buy_button(message: Message):
    await buy_command(message)

@dp.message(lambda message: message.text == "💰 کیف پول")
async def handle_balance_button(message: Message):
    await balance_command(message)

@dp.message(lambda message: message.text == "💳 افزایش موجودی")
async def handle_charge_button(message: Message, state: FSMContext):
    await charge_command(message, state)

@dp.message(lambda message: message.text == "📞 پشتیبانی")
async def handle_support_button(message: Message):
    await support_command(message)

@dp.message(lambda message: message.text == "ℹ️ راهنما")
async def handle_help_button(message: Message):
    await help_command(message)

# ========== سیستم شارژ کیف پول (FSM) ==========
@dp.message(ChargeStates.waiting_for_amount)
async def process_charge_amount(message: Message, state: FSMContext):
    try:
        amount = int(message.text)
        if amount < 100000:
            await message.answer("❌ حداقل مبلغ شارژ ۱۰۰,۰۰۰ تومان است. لطفاً مجدداً وارد کن.")
            return
        
        await state.update_data(amount=amount)
        await state.set_state(ChargeStates.waiting_for_receipt)
        await message.answer(
            f"✅ مبلغ {amount:,} تومان ثبت شد.\n\n"
            f"🏦 شماره کارت جهت واریز:\n"
            f"`{config.CARD_NUMBER}`\n"
            f"👤 به نام: دانیال بدری\n\n"
            "📸 لطفاً عکس رسید کارت به کارت خود را ارسال کنید.\n"
            "⚠️ فقط عکس (JPEG/PNG) پذیرفته می‌شود."
        )
    except ValueError:
        await message.answer("❌ لطفاً یک عدد معتبر وارد کن (مثلاً 100000)")

@dp.message(ChargeStates.waiting_for_receipt)
async def process_charge_receipt(message: Message, state: FSMContext):
    if not message.photo:
        await message.answer("❌ لطفاً یک عکس معتبر ارسال کن.")
        return
    
    photo = message.photo[-1]
    photo_id = photo.file_id
    
    data = await state.get_data()
    amount = data.get("amount")
    
    if not amount:
        await message.answer("❌ خطا در پردازش. لطفاً دوباره تلاش کن.")
        await state.clear()
        return
    
    # ذخیره در دیتابیس
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO charge_requests (user_id, amount, receipt_photo_id, status) VALUES (?, ?, ?, 'pending')",
            (message.from_user.id, amount, photo_id)
        )
        await db.commit()
    
    await state.clear()
    
    await message.answer(
        "✅ رسید شما دریافت شد.\n\n"
        "⏳ درخواست شما برای تأیید به ادمین ارسال شد.\n"
        "به محض تأیید، موجودی کیف پول شما شارژ می‌شود."
    )
    
    # نوتیفیکیشن به ادمین
    await notify_admin(message.from_user.id, amount)

# ========== مدیریت خرید (۳ مرحله) ==========
@dp.callback_query(lambda c: c.data == "select_duration_1m")
async def select_duration(callback: CallbackQuery):
    await callback.message.edit_text(
        "👤 تعداد کاربران مورد نظر را انتخاب کنید:",
        reply_markup=buy_user_count_keyboard()
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "select_user_1")
async def select_user_count(callback: CallbackQuery):
    await callback.message.edit_text(
        "📋 لیست تعرفه‌های ۱ ماهه / ۱ کاربره:\n\n"
        "یکی از گزینه‌های زیر رو انتخاب کن:",
        reply_markup=buy_plans_keyboard()
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data and c.data.startswith("buy_"))
async def buy_callback(callback: CallbackQuery):
    # ========== پاسخ سریع به کاربر ==========
    await callback.answer("✅ در حال ثبت درخواست...")
    
    data_parts = callback.data.split("_")
    if len(data_parts) < 4:
        await callback.message.edit_text("❌ اطلاعات ناقص است.")
        return
    
    price = data_parts[2].replace("k", "000")
    volume = data_parts[3].replace("gb", "GB")
    
    try:
        price_int = int(price)
    except:
        await callback.message.edit_text("❌ خطا در پردازش قیمت.")
        return
    
    user_id = callback.from_user.id
    plan_name = f"۱ ماهه - {volume}"
    
    try:
        # ========== ثبت درخواست در دیتابیس ==========
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "INSERT INTO service_requests (user_id, plan_name, status) VALUES (?, ?, 'pending')",
                (user_id, plan_name)
            )
            await db.commit()
        
        # ========== ارسال پیام به کاربر ==========
        await callback.message.edit_text(
            f"✅ درخواست سرویس شما با موفقیت ثبت شد!\n\n"
            f"📅 مدت: ۱ ماهه\n"
            f"👤 تعداد کاربر: ۱ کاربره\n"
            f"📊 حجم: {volume}\n"
            f"💰 قیمت: {price_int:,} تومان\n\n"
            f"⏳ کانفیگ شما به زودی توسط ادمین ارسال خواهد شد.\n"
            f"لطفاً صبور باشید."
        )
        
        # ========== ارسال نوتیفیکیشن به ادمین ==========
        await notify_admin_service(user_id, plan_name, price_int, volume)
        
    except Exception as e:
        await callback.message.edit_text(
            f"❌ خطا در ثبت درخواست:\n{str(e)}\n\n"
            "لطفاً دوباره تلاش کن یا با پشتیبانی تماس بگیر."
        )

# ========== دکمه‌های بازگشت ==========
@dp.callback_query(lambda c: c.data == "back_to_duration")
async def back_to_duration(callback: CallbackQuery):
    await callback.message.edit_text(
        "📅 مدت اشتراک خود را انتخاب کنید:",
        reply_markup=buy_main_keyboard()
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "back_to_user_count")
async def back_to_user_count(callback: CallbackQuery):
    await callback.message.edit_text(
        "👤 تعداد کاربران مورد نظر را انتخاب کنید:",
        reply_markup=buy_user_count_keyboard()
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(
        "🔙 به منوی اصلی برگشتید.",
        reply_markup=main_menu_keyboard()
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "back_to_admin")
async def back_to_admin(callback: CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(
        "👋 به پنل مدیریت خوش اومدی!",
        reply_markup=admin_panel_keyboard()
    )
    await callback.answer()

# ========== مدیریت درخواست‌های سرویس (ادمین) ==========
@dp.callback_query(lambda c: c.data.startswith("send_config_"))
async def send_config(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی ندارید.", show_alert=True)
        return
    
    request_id = int(callback.data.split("_")[2])
    
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT user_id FROM service_requests WHERE id = ? AND status = 'pending'",
            (request_id,)
        )
        result = await cursor.fetchone()
        
        if not result:
            await callback.message.edit_text("❌ این درخواست قبلاً پردازش شده یا وجود ندارد.")
            await callback.answer()
            return
        
        user_id = result[0]
    
    await callback.message.edit_text(
        f"📤 لطفاً کانفیگ را برای کاربر {user_id} ارسال کن:\n\n"
        f"از دستور زیر استفاده کن:\n"
        f"`/send {user_id} [متن کانفیگ]`"
    )
    await callback.answer()

# ========== مدیریت درخواست‌های شارژ (ادمین) ==========
@dp.callback_query(lambda c: c.data.startswith("approve_charge_") or c.data.startswith("reject_charge_"))
async def handle_charge_request(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی ندارید.", show_alert=True)
        return
    
    # استخراج شناسه درخواست و نوع عملیات
    parts = callback.data.split("_")
    action = parts[0]  # approve یا reject
    request_id = int(parts[2])  # شناسه درخواست
    
    async with aiosqlite.connect(DB_PATH) as db:
        # دریافت اطلاعات درخواست
        cursor = await db.execute(
            "SELECT user_id, amount FROM charge_requests WHERE id = ? AND status = 'pending'",
            (request_id,)
        )
        request = await cursor.fetchone()
        
        if not request:
            await callback.message.edit_text("❌ این درخواست قبلاً پردازش شده یا وجود ندارد.")
            await callback.answer()
            return
        
        user_id, amount = request
        
        if action == "approve":
            # تأیید: افزایش موجودی کاربر
            await db.execute(
                "UPDATE users SET balance = balance + ? WHERE id = ?",
                (amount, user_id)
            )
            await db.execute(
                "UPDATE charge_requests SET status = 'approved', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (request_id,)
            )
            await db.commit()
            
            # ارسال پیام به کاربر
            try:
                await bot.send_message(
                    user_id,
                    f"✅ درخواست شارژ شما به مبلغ {amount:,} تومان تأیید شد!\n"
                    f"💰 موجودی جدید شما: +{amount:,} تومان"
                )
            except:
                pass
            
            await callback.message.edit_text(
                f"✅ درخواست {request_id} تأیید شد.\n"
                f"👤 کاربر {user_id} به مبلغ {amount:,} تومان شارژ شد."
            )
            
        else:  # reject
            await db.execute(
                "UPDATE charge_requests SET status = 'rejected', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (request_id,)
            )
            await db.commit()
            
            # ارسال پیام به کاربر
            try:
                await bot.send_message(
                    user_id,
                    f"❌ درخواست شارژ شما به مبلغ {amount:,} تومان رد شد.\n"
                    f"در صورت نیاز با پشتیبانی تماس بگیرید."
                )
            except:
                pass
            
            await callback.message.edit_text(
                f"❌ درخواست {request_id} رد شد.\n"
                f"👤 کاربر {user_id} از شارژ {amount:,} تومانی محروم شد."
            )
    
    await callback.answer()

# ========== دستورات ادمین ==========
@dp.message(Command("admin"))
async def admin_command(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    await message.answer(
        "👋 به پنل مدیریت خوش اومدی!",
        reply_markup=admin_panel_keyboard()
    )

@dp.callback_query(lambda c: c.data and c.data.startswith("admin_"))
async def admin_callback(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی ندارید.", show_alert=True)
        return
    
    if callback.data == "admin_users":
        from admin import admin_users
        await admin_users(callback)
    elif callback.data == "admin_stats":
        from admin import admin_stats
        await admin_stats(callback)
    elif callback.data == "admin_add_balance":
        from admin import admin_add_balance
        await admin_add_balance(callback)
    elif callback.data == "admin_charge_requests":
        from admin import admin_charge_requests
        await admin_charge_requests(callback)
    elif callback.data == "admin_service_requests":
        from admin import admin_service_requests
        await admin_service_requests(callback)
    else:
        await callback.answer("⏳ این بخش در حال توسعه است.", show_alert=True)

# ========== اجرای اصلی ==========
async def main():
    try:
        await init_db()
        print("✅ دیتابیس راه‌اندازی شد!")
        print("🤖 ربات در حال اجراست...")
        await dp.start_polling(bot)
    except Exception as e:
        print(f"❌ خطا: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
