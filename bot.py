import asyncio
import logging
import sys
import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from config import config
from database import init_db
from admin import is_admin
from keyboards import main_menu_keyboard, buy_main_keyboard, buy_user_count_keyboard, buy_plans_keyboard, admin_panel_keyboard

logging.basicConfig(level=logging.INFO)

bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

DB_PATH = config.DATABASE_URL.replace("sqlite+aiosqlite:///", "")

# ---------- دستورات عمومی ----------
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
        "3️⃣ اگه سوالی داری /support بزن.\n\n"
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
        "💳 برای شارژ کیف پول، به زودی درگاه پرداخت اضافه می‌شه."
    )

@dp.message(Command("support"))
async def support_command(message: Message):
    await message.answer(
        "📞 پشتیبانی:\n\n"
        "برای ارتباط با ادمین، از لینک زیر استفاده کن:\n"
        "@Dni2003\n\n"
        "⏰ پاسخگویی: ۹ صبح تا ۱۲ شب"
    )

# ---------- مدیریت دکمه‌های شیشه‌ای (ReplyKeyboard) ----------
@dp.message(lambda message: message.text == "🛒 خرید اشتراک")
async def handle_buy_button(message: Message):
    await buy_command(message)

@dp.message(lambda message: message.text == "💰 کیف پول")
async def handle_balance_button(message: Message):
    await balance_command(message)

@dp.message(lambda message: message.text == "📞 پشتیبانی")
async def handle_support_button(message: Message):
    await support_command(message)

@dp.message(lambda message: message.text == "ℹ️ راهنما")
async def handle_help_button(message: Message):
    await help_command(message)

# ---------- مدیریت خرید (۳ مرحله) ----------
# مرحله ۱: انتخاب مدت
@dp.callback_query(lambda c: c.data == "select_duration_1m")
async def select_duration(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "👤 تعداد کاربران مورد نظر را انتخاب کنید:",
        reply_markup=buy_user_count_keyboard()
    )
    await callback.answer()

# مرحله ۲: انتخاب تعداد کاربر
@dp.callback_query(lambda c: c.data == "select_user_1")
async def select_user_count(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "📋 لیست تعرفه‌های ۱ ماهه / ۱ کاربره:\n\n"
        "یکی از گزینه‌های زیر رو انتخاب کن:",
        reply_markup=buy_plans_keyboard()
    )
    await callback.answer()

# مرحله ۳: نمایش تعرفه انتخاب شده
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

# دکمه‌های بازگشت
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

# ---------- دستورات ادمین ----------
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

# ---------- اجرای ربات ----------
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
