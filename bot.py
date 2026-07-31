import asyncio
import logging
import sys
import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
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
        "🔹 حداقل مبلغ: ۱۰,۰۰۰ تومان"
    )

# ========== مدیریت دکمه‌های شیشه‌ای (ReplyKeyboard) ==========
@dp.message(lambda message: message.text == "🛒 خرید اشتراک")
async def handle_buy_button(message: Message):
    await buy_command(message)

@dp.message(lambda message: message.text == "💰 کیف پول")
async def handle_balance_button(message: Message):
    await balance_command(message)

@dp.message(lambda message: message.text == "💳 شارژ کیف پول")
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
        if amount < 10000:
            await message.answer("❌ حداقل مبلغ شارژ ۱۰,۰۰۰ تومان است. لطفاً مجدداً وارد کن.")
            return
        
        await state.update_data(amount=amount)
        await state.set_state(ChargeStates.waiting_for_receipt)
        await message.answer(
            f"✅ مبلغ {amount:,} تومان ثبت شد.\n\n"
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
async def select_duration(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "👤 تعداد کاربران مورد نظر را انتخاب کنید:",
        reply_markup=buy_user_count_keyboard()
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "select_user_1")
async def select_user_count(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📋 لیست تعرفه‌های ۱ ماهه / ۱ کاربره:\n\n"
        "یکی از گزینه‌های زیر رو انتخاب کن:",
        reply_markup=buy_plans_keyboard()
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data and c.data.startswith("buy_"))
async def buy_callback(callback: types.CallbackQuery):
    data_parts = callback.data.split("_")
    if len(data_parts) < 4:
        await callback.answer("❌ اطلاعات ناقص است.", show_alert=True)
        return
    
    price = data_parts[2].replace("k", "000")
    volume = data_parts[3].replace("gb", "GB")
    
    try:
        price_int = int(price)
    except:
        await callback.answer("❌ خطا در پردازش قیمت.", show_alert=True)
        return
    
    await callback.message.edit_text(
        f"✅ تعرفه انتخاب شده:\n\n"
        f"📅 مدت: ۱ ماهه\n"
        f"👤 تعداد کاربر: ۱ کاربره\n"
        f"💰 قیمت: {price_int:,} تومان\n"
        f"📊 حجم: {volume}\n\n"
        f"🔜 به زودی امکان خرید و پرداخت فعال می‌شود."
    )
    await callback.answer()

# ========== دکمه‌های بازگشت ==========
@dp.callback_query(lambda c: c.data == "back_to_duration")
async def back_to_duration(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📅 مدت اشتراک خود را انتخاب کنید:",
        reply_markup=buy_main_keyboard()
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "back_to_user_count")
async def back_to_user_count(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "👤 تعداد کاربران مورد نظر را انتخاب کنید:",
        reply_markup=buy_user_count_keyboard()
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "back_to_main")
async def back_to_main(callback: types.CallbackQuery):
    await callback.message.delete()
    await callback.message.answer(
        "🔙 به منوی اصلی برگشتید.",
        reply_markup=main_menu_keyboard()
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
async def admin_callback(callback: types.CallbackQuery):
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
