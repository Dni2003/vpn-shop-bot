from keyboards import main_menu_keyboard, buy_plans_keyboard, admin_panel_keyboard
import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from config import config
from database import init_db
from admin import admin_panel, admin_users, admin_stats, admin_add_balance, is_admin

# تنظیم لاگ
logging.basicConfig(level=logging.INFO)

# راه‌اندازی ربات
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

# دستور /start
@dp.message(Command("start"))
async def start_command(message: Message):
    user = message.from_user
    # ثبت کاربر در دیتابیس
    async with await get_db() as db:
        await db.execute(
            "INSERT OR IGNORE INTO users (id, username, first_name, last_name) VALUES (?, ?, ?, ?)",
            (user.id, user.username, user.first_name, user.last_name)
        )
        await db.commit()
    
    await message.answer(
        f"👋 سلام {user.first_name}!\n"
        "به ربات فروش VPN خوش اومدی! 🌟\n\n"
        "از دکمه‌های زیر استفاده کن:",
        reply_markup=main_menu_keyboard()  # کیبورد شیشه‌ای
    )

# دستور /help
@dp.message(Command("help"))
async def help_command(message: Message):
    await message.answer(
        "🤖 راهنمای ربات:\n\n"
        "1️⃣ برای خرید اشتراک از /buy استفاده کن.\n"
        "2️⃣ موجودی خودت رو با /balance ببین.\n"
        "3️⃣ اگه سوالی داری /support بزن.\n\n"
        "💡 در حال توسعه! امکانات بیشتر به زودی..."
    )

# دستور /buy (نمونه)
@dp.message(Command("buy"))
async def buy_command(message: Message):
    await message.answer(
        "🛒 لیست پلن‌های VPN:\n\n"
        "یکی از گزینه‌های زیر رو انتخاب کن:",
        reply_markup=buy_plans_keyboard()
    )

# دستور /balance
@dp.message(Command("balance"))
async def balance_command(message: Message):
    await message.answer(
        "💰 موجودی کیف پول شما:\n"
        "۰ تومان\n\n"
        "💳 برای شارژ کیف پول، به زودی درگاه پرداخت اضافه می‌شه."
    )

# دستور /support
@dp.message(Command("support"))
async def support_command(message: Message):
    await message.answer(
        "📞 پشتیبانی:\n\n"
        "برای ارتباط با ادمین، از لینک زیر استفاده کن:\n"
        "@Dni2003\n\n"
        "⏰ پاسخگویی: ۹ صبح تا ۱۲ شب"
    )

# اجرای ربات
async def main():
    # راه‌اندازی دیتابیس
    await init_db()
    print("✅ دیتابیس راه‌اندازی شد!")
    
    # شروع ربات
    print("🤖 ربات در حال اجراست...")
    await dp.start_polling(bot)
    
@dp.message(Command("admin"))
async def admin_command(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    await admin_panel(message)

@dp.callback_query(lambda c: c.data and c.data.startswith("admin_"))
async def admin_callback(callback: types.CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی ندارید.", show_alert=True)
        return
    
    if callback.data == "admin_users":
        await admin_users(callback)
    elif callback.data == "admin_stats":
        await admin_stats(callback)
    elif callback.data == "admin_add_balance":
        await admin_add_balance(callback)
    else:
        await callback.answer("این بخش در حال توسعه است.")

if __name__ == "__main__":
    asyncio.run(main())
