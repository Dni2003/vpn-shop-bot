import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message
from config import config
from database import init_db

# تنظیم لاگ
logging.basicConfig(level=logging.INFO)

# راه‌اندازی ربات
bot = Bot(token=config.BOT_TOKEN)
dp = Dispatcher()

# دستور /start
@dp.message(Command("start"))
async def start_command(message: Message):
    user = message.from_user
    await message.answer(
        f"👋 سلام {user.first_name}!\n"
        "به ربات فروش VPN خوش اومدی!\n\n"
        "📌 دستورات موجود:\n"
        "/start - شروع مجدد\n"
        "/help - راهنما\n"
        "/buy - خرید اشتراک VPN\n"
        "/balance - موجودی کیف پول\n"
        "/support - پشتیبانی"
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
        "1️⃣ ۱ ماهه - ۱۰۰,۰۰۰ تومان\n"
        "2️⃣ ۳ ماهه - ۲۵۰,۰۰۰ تومان\n"
        "3️⃣ ۶ ماهه - ۴۵۰,۰۰۰ تومان\n"
        "4️⃣ ۱ ساله - ۷۵۰,۰۰۰ تومان\n\n"
        "🔜 به زودی امکان خرید مستقیم فعال می‌شه!"
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

if __name__ == "__main__":
    asyncio.run(main())
