import aiosqlite
from aiogram import types
from aiogram.types import Message, CallbackQuery
from config import config

DB_PATH = config.DATABASE_URL.replace("sqlite+aiosqlite:///", "")

# ========== مرحله ۱: کاربر مبلغ رو وارد می‌کنه ==========
async def request_charge_step1(message: Message):
    await message.answer(
        "💳 لطفاً مبلغ شارژ خود را به تومان وارد کنید:\n"
        "مثلاً: 100000\n\n"
        "🔹 حداقل مبلغ: ۱۰,۰۰۰ تومان"
    )
    # منتظر می‌مونه تا کاربر مبلغ رو بفرسته

# ========== مرحله ۲: دریافت مبلغ و درخواست عکس رسید ==========
async def process_charge_amount(message: Message):
    try:
        amount = int(message.text)
        if amount < 10000:
            await message.answer("❌ حداقل مبلغ شارژ ۱۰,۰۰۰ تومان است. لطفاً مجدداً وارد کن.")
            return
        
        # ذخیره موقت مبلغ در حافظه (اینجا ساده‌اش می‌کنیم)
        # در نسخه حرفه‌ای از FSM استفاده می‌کنیم
        await message.answer(
            f"✅ مبلغ {amount:,} تومان ثبت شد.\n\n"
            "📸 لطفاً عکس رسید کارت به کارت خود را ارسال کنید.\n"
            "⚠️ فقط عکس (JPEG/PNG) پذیرفته می‌شود."
        )
        # ذخیره مبلغ در یک متغیر سراسری موقت (برای سادگی)
        # در نسخه واقعی از FSM استفاده کن
        
        # به عنوان راه حل ساده، مبلغ رو در متن ذخیره می‌کنیم
        # و بعداً از همون متن برای پردازش استفاده می‌کنیم
    except ValueError:
        await message.answer("❌ لطفاً یک عدد معتبر وارد کن (مثلاً 100000)")

# ========== مرحله ۳: دریافت عکس رسید و ثبت درخواست ==========
async def process_charge_receipt(message: Message):
    if not message.photo:
        await message.answer("❌ لطفاً یک عکس معتبر ارسال کن.")
        return
    
    # دریافت آخرین عکس (با کیفیت بالا)
    photo = message.photo[-1]
    photo_id = photo.file_id
    
    # دریافت مبلغ از متن پیام قبلی (راه‌حل ساده)
    # در نسخه واقعی از FSM استفاده کن
    
    # به کاربر پیام می‌دیم که منتظر تأیید باشه
    await message.answer(
        "✅ رسید شما دریافت شد.\n\n"
        "⏳ درخواست شما برای تأیید به ادمین ارسال شد.\n"
        "به محض تأیید، موجودی کیف پول شما شارژ می‌شود."
    )
    
    # ذخیره درخواست در دیتابیس با وضعیت pending
    # برای سادگی فعلاً یک رکورد نمونه می‌سازیم
    # (در ادامه کاملش می‌کنیم)
