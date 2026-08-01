import asyncio
import logging
import sys
import aiosqlite
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramBadRequest

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
from broadcast_states import BroadcastStates
from discount_states import DiscountStates
from settings_states import SettingsStates
from support_states import SupportStates
from discount_logic import validate_discount_code, apply_discount
from expiry_manager import (
    check_and_update_expired,
    get_user_active_service,
)
from settings_manager import get_setting, set_setting, get_all_settings
from support_manager import save_admin_reply, get_user_by_admin_message

# ========== تنظیمات اولیه ==========
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

bot = Bot(token=config.BOT_TOKEN)
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

DB_PATH = config.DATABASE_URL.replace("sqlite+aiosqlite:///", "")

# ========== توابع کمکی ==========
async def notify_admin(user_id: int, amount: int):
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

async def process_purchase(message: Message, state: FSMContext, callback: CallbackQuery = None):
    """پردازش نهایی خرید با یا بدون تخفیف"""
    data = await state.get_data()
    user_id = data.get("user_id") or message.from_user.id
    plan_name = data.get("plan_name")
    volume = data.get("volume")
    original_price = data.get("price")
    final_price = data.get("final_price", original_price)
    discount_code = data.get("discount_code")
    discount_code_id = data.get("discount_code_id")
    
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
            result = await cursor.fetchone()
            balance = result[0] if result else 0
        
        if balance < final_price:
            msg = f"❌ موجودی کافی نیست!\n\n"
            msg += f"💰 موجودی: {balance:,} تومان\n"
            if discount_code:
                msg += f"💰 قیمت اصلی: {original_price:,} تومان\n"
                msg += f"🎟 قیمت با تخفیف: {final_price:,} تومان\n"
            else:
                msg += f"💰 قیمت: {final_price:,} تومان\n"
            msg += f"\n⚠️ لطفاً حساب خود را شارژ کنید."
            
            if callback:
                await callback.message.edit_text(msg)
            else:
                await message.answer(msg)
            await state.clear()
            return
        
        expires_at = (datetime.now() + timedelta(days=30)).isoformat()
        description = f"خرید {plan_name}"
        if discount_code:
            description += f" (با تخفیف {discount_code})"
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE users SET balance = balance - ? WHERE id = ?",
                (final_price, user_id)
            )
            await db.execute(
                "INSERT INTO service_requests (user_id, plan_name, volume, price, status, expires_at) VALUES (?, ?, ?, ?, 'active', ?)",
                (user_id, plan_name, volume, final_price, expires_at)
            )
            await db.execute(
                "INSERT INTO transactions (user_id, amount, type, description, status) VALUES (?, ?, 'purchase', ?, 'completed')",
                (user_id, final_price, description)
            )
            if discount_code_id:
                await db.execute(
                    "UPDATE discount_codes SET used_count = used_count + 1 WHERE id = ?",
                    (discount_code_id,)
                )
                await db.execute(
                    "INSERT INTO discount_usage (user_id, discount_code_id) VALUES (?, ?)",
                    (user_id, discount_code_id)
                )
            await db.commit()
        
        balance_new = balance - final_price
        
        msg = f"✅ خرید شما با موفقیت انجام شد!\n\n"
        msg += f"📅 مدت: ۱ ماهه\n"
        msg += f"📊 حجم: {volume}\n"
        if discount_code:
            msg += f"💰 قیمت اصلی: {original_price:,} تومان\n"
            msg += f"🎟 تخفیف اعمال‌شده: {discount_code}\n"
            msg += f"💰 قیمت نهایی: {final_price:,} تومان\n"
        else:
            msg += f"💰 قیمت: {final_price:,} تومان\n"
        msg += f"💰 موجودی جدید: {balance_new:,} تومان\n"
        msg += f"📆 تاریخ انقضا: {(datetime.now() + timedelta(days=30)).strftime('%Y-%m-%d')}\n\n"
        msg += f"⏳ کانفیگ به زودی توسط ادمین ارسال خواهد شد."
        
        if callback:
            await callback.message.edit_text(msg)
        else:
            await message.answer(msg)
        
        await notify_admin_service(user_id, plan_name, final_price, volume)
        await state.clear()
        
    except Exception as e:
        error_msg = f"❌ خطا در پردازش خرید: {str(e)}"
        if callback:
            await callback.message.edit_text(error_msg)
        else:
            await message.answer(error_msg)
        await state.clear()

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
    
    welcome_msg = await get_setting("welcome_message") or "👋 سلام {first_name}!\nبه ربات خرید فیلترشکن خوش آمدید ❗️\nجهت خرید فیلترشکن از دکمه‌های زیر استفاده کنید:"
    welcome_msg = welcome_msg.format(first_name=user.first_name)
    
    service = await get_user_active_service(user.id)
    expiry_message = ""
    if service:
        plan_name, volume, expires_at = service
        expire_date = datetime.fromisoformat(expires_at)
        now = datetime.now()
        days_left = (expire_date - now).days
        
        if days_left < 0:
            expiry_message = f"\n\n⛔ سرویس {plan_name} شما منقضی شده است!"
        elif days_left <= 3:
            expiry_message = f"\n\n⚠️ سرویس {plan_name} شما در {days_left} روز دیگر منقضی می‌شود."
    
    await message.answer(
        welcome_msg + expiry_message,
        reply_markup=main_menu_keyboard()
    )

@dp.message(Command("help"))
async def help_command(message: Message):
    await message.answer(
        "🤖 راهنمای ربات:\n\n"
        "1️⃣ برای خرید سرویس از دکمه خرید سرویس استفاده کن.\n"
        "2️⃣ موجودی خودت رو با حساب کاربری ببین.\n"
        "3️⃣ برای شارژ کیف پول از شارژ کیف پول استفاده کن.\n"
        "4️⃣ اگه سوالی داری پشتیبانی رو بزن."
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
    
    service = await get_user_active_service(user_id)
    service_text = ""
    if service:
        plan_name, volume, expires_at = service
        expire_date = datetime.fromisoformat(expires_at)
        now = datetime.now()
        days_left = (expire_date - now).days
        service_text = f"\n\n📦 سرویس فعال: {plan_name}\n📊 حجم: {volume}\n⏳ روزهای باقیمانده: {days_left} روز"
    else:
        service_text = "\n\n📭 هیچ سرویس فعالی ندارید."
    
    await message.answer(
        f"💰 موجودی کیف پول شما:\n"
        f"{balance:,} تومان"
        f"{service_text}",
        reply_markup=back_to_main_keyboard()  # <-- اضافه شد
    )


@dp.message(Command("support"))
async def support_command(message: Message, state: FSMContext):
    await state.set_state(SupportStates.waiting_for_message)
    await message.answer(
        "📩 لطفاً پیام خود را برای پشتیبانی ارسال کنید.\n"
        "پس از ارسال، پیام شما به ادمین ارسال خواهد شد."
    )

@dp.message(Command("charge"))
async def charge_command(message: Message, state: FSMContext):
    min_charge = await get_setting("min_charge_amount") or "100000"
    await state.set_state(ChargeStates.waiting_for_amount)
    await message.answer(
        f"💳 لطفاً مبلغ شارژ خود را به تومان وارد کنید:\n"
        f"مثلاً: 100000\n\n"
        f"🔹 حداقل مبلغ: {int(min_charge):,} تومان"
    )

@dp.message(Command("my_services"))
async def my_services_command(message: Message):
    user_id = message.from_user.id
    
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT plan_name, volume, price, expires_at, status FROM service_requests WHERE user_id = ? ORDER BY created_at DESC LIMIT 5",
            (user_id,)
        )
        services = await cursor.fetchall()
    
    if not services:
        await message.answer("📭 شما هیچ سرویس فعال یا قبلی ندارید.")
        return
    
    text = "📦 لیست سرویس‌های شما (۵ مورد آخر):\n\n"
    for service in services:
        plan_name, volume, price, expires_at, status = service
        
        if status == "active":
            try:
                expire_date = datetime.fromisoformat(expires_at)
                days_left = (expire_date - datetime.now()).days
                if days_left < 0:
                    status_emoji = "⛔ منقضی شده"
                else:
                    status_emoji = f"✅ فعال ({days_left} روز)"
            except:
                status_emoji = "✅ فعال"
        elif status == "pending":
            status_emoji = "⏳ در انتظار ارسال کانفیگ"
        elif status == "sent":
            status_emoji = "📤 کانفیگ ارسال شده"
        else:
            status_emoji = "❓ نامشخص"
        
        text += f"📌 {plan_name}\n"
        text += f"   📊 حجم: {volume}\n"
        text += f"   💰 قیمت: {price:,} تومان\n"
        text += f"   📆 وضعیت: {status_emoji}\n"
        text += f"   🕒 انقضا: {expires_at or 'نامشخص'}\n"
        text += "─" * 20 + "\n"
    
    await message.answer(text)

# ========== دستورات ادمین ==========
@dp.message(Command("add_balance"))
async def add_balance_command(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ شما دسترسی ندارید.")
        return
    
    args = message.text.split()
    if len(args) != 3:
        await message.answer(
            "❌ فرمت صحیح:\n"
            "/add_balance [USER_ID] [AMOUNT]\n"
            "مثال: /add_balance 123456789 50000"
        )
        return
    
    try:
        user_id = int(args[1])
        amount = int(args[2])
    except ValueError:
        await message.answer("❌ لطفاً آیدی و مبلغ را به عدد وارد کن.")
        return
    
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT id FROM users WHERE id = ?", (user_id,))
        if not await cursor.fetchone():
            await message.answer("❌ کاربری با این آیدی پیدا نشد.")
            return
        
        await db.execute(
            "UPDATE users SET balance = balance + ? WHERE id = ?",
            (amount, user_id)
        )
        await db.commit()
    
    await message.answer(f"✅ مبلغ {amount:,} تومان به کاربر {user_id} اضافه شد!")

@dp.message(Command("admin"))
async def admin_command(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ شما دسترسی به این بخش ندارید.")
        return
    await message.answer(
        "👋 به پنل مدیریت خوش اومدی!",
        reply_markup=admin_panel_keyboard()
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
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE service_requests SET status = 'sent' WHERE user_id = ? AND status = 'active'",
                (user_id,)
            )
            await db.commit()
        
        await message.answer(f"✅ کانفیگ به کاربر {user_id} ارسال شد.")
        
    except Exception as e:
        await message.answer(f"❌ خطا در ارسال کانفیگ: {str(e)}")

# ========== دستور جستجوی تراکنش کاربر ==========
@dp.message(Command("search_trans"))
async def search_trans_command(message: Message):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ شما دسترسی ندارید.")
        return
    
    args = message.text.split()
    if len(args) != 2:
        await message.answer("❌ فرمت صحیح:\n/search_trans [USER_ID]")
        return
    
    try:
        user_id = int(args[1])
    except ValueError:
        await message.answer("❌ لطفاً یک آیدی عددی وارد کن.")
        return
    
    from admin import to_tehran_time
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            cursor = await db.execute(
                "SELECT id, amount, type, description, status, created_at FROM transactions WHERE user_id = ? ORDER BY created_at DESC LIMIT 20",
                (user_id,)
            )
            transactions = await cursor.fetchall()
        
        if not transactions:
            await message.answer(f"📭 کاربر {user_id} هیچ تراکنشی ندارد.")
            return
        
        text = f"📋 تراکنش‌های کاربر {user_id} (۲۰ مورد آخر):\n\n"
        for trans in transactions:
            trans_id, amount, trans_type, desc, status, created_at = trans
            local_time = to_tehran_time(created_at)
            type_emoji = "💳" if trans_type == "deposit" else "🛒"
            status_emoji = "✅" if status == "completed" else "⏳" if status == "pending" else "❌"
            
            text += f"{type_emoji} #{trans_id} | {amount:,} تومان\n"
            text += f"   {desc or '-'} | {status_emoji} {status}\n"
            text += f"   🕒 {local_time}\n"
            text += "─" * 20 + "\n"
        
        await message.answer(text)
        
    except Exception as e:
        await message.answer(f"❌ خطا: {str(e)}")

# ========== دستور لغو عملیات ==========
@dp.message(Command("cancel"))
async def cancel_command(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("❌ عملیات لغو شد.")

# ========== مدیریت منوی اصلی (دکمه‌های اینلاین) ==========
@dp.callback_query(lambda c: c.data.startswith("menu_"))
async def main_menu_callback(callback: CallbackQuery, state: FSMContext):
    if callback.data == "menu_buy":
        await buy_command(callback.message)
        await callback.message.delete()
        await callback.answer()
    
    elif callback.data == "menu_account":
        await balance_command(callback.message)
        await callback.message.delete()
        await callback.answer()
    
    elif callback.data == "menu_services":
        await my_services_command(callback.message)
        await callback.message.delete()
        await callback.answer()
    
    elif callback.data == "menu_support":
        await support_command(callback.message, state)
        await callback.message.delete()
        await callback.answer()
    
    elif callback.data == "menu_charge":
        await charge_command(callback.message, state)
        await callback.message.delete()
        await callback.answer()
    
    elif callback.data == "menu_close":
        await callback.message.delete()
        await callback.answer()

# ========== سیستم پشتیبانی (FSM - دریافت پیام از کاربر) ==========
@dp.message(SupportStates.waiting_for_message)
async def process_support_message(message: Message, state: FSMContext):
    user_id = message.from_user.id
    user_name = message.from_user.first_name
    username = message.from_user.username or "بدون نام کاربری"
    
    # پیام ارسال به ادمین
    for admin_id in config.ADMIN_IDS:
        try:
            # ارسال پیام با محتوای مناسب
            if message.text:
                sent_msg = await bot.send_message(
                    admin_id,
                    f"📩 پیام جدید از {user_name} (@{username}) [ID: {user_id}]:\n\n{message.text}"
                )
                await save_admin_reply(sent_msg.message_id, user_id)
            
            elif message.photo:
                # ارسال عکس با کپشن
                caption = f"📸 عکس از {user_name} (@{username}) [ID: {user_id}]"
                if message.caption:
                    caption += f"\n\n📝 متن: {message.caption}"
                sent_msg = await bot.send_photo(
                    admin_id,
                    message.photo[-1].file_id,
                    caption=caption
                )
                await save_admin_reply(sent_msg.message_id, user_id)
            
            elif message.video:
                caption = f"🎥 ویدئو از {user_name} (@{username}) [ID: {user_id}]"
                if message.caption:
                    caption += f"\n\n📝 متن: {message.caption}"
                sent_msg = await bot.send_video(
                    admin_id,
                    message.video.file_id,
                    caption=caption
                )
                await save_admin_reply(sent_msg.message_id, user_id)
            
            elif message.document:
                caption = f"📄 فایل از {user_name} (@{username}) [ID: {user_id}]"
                if message.caption:
                    caption += f"\n\n📝 متن: {message.caption}"
                sent_msg = await bot.send_document(
                    admin_id,
                    message.document.file_id,
                    caption=caption
                )
                await save_admin_reply(sent_msg.message_id, user_id)
            
            elif message.audio or message.voice:
                caption = f"🎵 فایل صوتی از {user_name} (@{username}) [ID: {user_id}]"
                if message.caption:
                    caption += f"\n\n📝 متن: {message.caption}"
                file_id = message.audio.file_id if message.audio else message.voice.file_id
                sent_msg = await bot.send_audio(
                    admin_id,
                    file_id,
                    caption=caption
                )
                await save_admin_reply(sent_msg.message_id, user_id)
            
            else:
                # سایر محتواها (استیکر، ایموجی و ...)
                sent_msg = await bot.send_message(
                    admin_id,
                    f"📩 پیام جدید از {user_name} (@{username}) [ID: {user_id}]:\n\n"
                    f"(نوع پیام قابل نمایش نیست، لطفاً در تلگرام مشاهده کنید)"
                )
                await save_admin_reply(sent_msg.message_id, user_id)
                
        except Exception as e:
            logger.error(f"❌ خطا در ارسال پیام به ادمین: {e}")
    
    await message.answer("✅ پیام شما به ادمین ارسال شد.\n⏳ منتظر پاسخ باشید.")
    await state.clear()

# ========== سیستم پشتیبانی (پاسخ ادمین با ریپلای) ==========
@dp.message()
async def handle_admin_reply(message: Message):
    # فقط ادمین‌ها می‌توانند ریپلای بزنند
    if message.from_user.id not in config.ADMIN_IDS:
        return
    
    # بررسی اینکه آیا پیام ریپلای است
    if not message.reply_to_message:
        return
    
    # دریافت message_id پیامی که ادمین روش ریپلای زده
    replied_message_id = message.reply_to_message.message_id
    
    # دریافت user_id از دیتابیس
    user_id = await get_user_by_admin_message(replied_message_id)
    
    if not user_id:
        await message.answer("⚠️ این پیام قابل پاسخگویی نیست.")
        return
    
    try:
        # ========== ارسال پاسخ به کاربر بر اساس نوع محتوا ==========
        if message.text:
            await bot.send_message(
                user_id,
                f"📨 پاسخ پشتیبانی:\n\n{message.text}"
            )
        
        elif message.photo:
            caption = f"📨 پاسخ پشتیبانی"
            if message.caption:
                caption += f":\n\n{message.caption}"
            await bot.send_photo(
                user_id,
                message.photo[-1].file_id,
                caption=caption
            )
        
        elif message.video:
            caption = f"📨 پاسخ پشتیبانی"
            if message.caption:
                caption += f":\n\n{message.caption}"
            await bot.send_video(
                user_id,
                message.video.file_id,
                caption=caption
            )
        
        elif message.document:
            caption = f"📨 پاسخ پشتیبانی"
            if message.caption:
                caption += f":\n\n{message.caption}"
            await bot.send_document(
                user_id,
                message.document.file_id,
                caption=caption
            )
        
        elif message.audio:
            caption = f"📨 پاسخ پشتیبانی"
            if message.caption:
                caption += f":\n\n{message.caption}"
            await bot.send_audio(
                user_id,
                message.audio.file_id,
                caption=caption
            )
        
        elif message.voice:
            caption = f"📨 پاسخ پشتیبانی"
            if message.caption:
                caption += f":\n\n{message.caption}"
            await bot.send_voice(
                user_id,
                message.voice.file_id,
                caption=caption
            )
        
        elif message.sticker:
            await bot.send_sticker(
                user_id,
                message.sticker.file_id
            )
        
        else:
            await bot.send_message(
                user_id,
                f"📨 پاسخ پشتیبانی:\n\n(نوع پیام قابل نمایش نیست، لطفاً در تلگرام مشاهده کنید)"
            )
        
        await message.answer(f"✅ پاسخ به کاربر {user_id} ارسال شد.")
        
    except Exception as e:
        await message.answer(f"❌ خطا در ارسال پاسخ: {str(e)}")


# ========== سیستم شارژ کیف پول (FSM) ==========
@dp.message(ChargeStates.waiting_for_amount)
async def process_charge_amount(message: Message, state: FSMContext):
    min_charge = await get_setting("min_charge_amount") or "100000"
    try:
        amount = int(message.text)
        if amount < int(min_charge):
            await message.answer(f"❌ حداقل مبلغ شارژ {int(min_charge):,} تومان است.")
            return
        
        await state.update_data(amount=amount)
        await state.set_state(ChargeStates.waiting_for_receipt)
        await message.answer(
            f"✅ مبلغ {amount:,} تومان ثبت شد.\n\n"
            f"🏦 شماره کارت جهت واریز:\n"
            f"`{config.CARD_NUMBER}`\n"
            f"👤 به نام: دانیال بدری\n\n"
            "📸 لطفاً عکس رسید خود را ارسال کنید."
        )
    except ValueError:
        await message.answer("❌ لطفاً یک عدد معتبر وارد کن.")

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
        await message.answer("❌ خطا در پردازش.")
        await state.clear()
        return
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO charge_requests (user_id, amount, receipt_photo_id, status) VALUES (?, ?, ?, 'pending')",
            (message.from_user.id, amount, photo_id)
        )
        await db.commit()
    
    await state.clear()
    
    await message.answer(
        "✅ رسید شما دریافت شد.\n\n"
        "⏳ درخواست شما برای تأیید به ادمین ارسال شد."
    )
    
    await notify_admin(message.from_user.id, amount)

# ========== سیستم ارسال پیام گروهی (FSM) ==========
@dp.message(BroadcastStates.waiting_for_text)
async def process_broadcast_text(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ شما دسترسی ندارید.")
        await state.clear()
        return
    
    data = await state.get_data()
    filter_type = data.get("filter_type", "all")
    text = message.text
    
    async with aiosqlite.connect(DB_PATH) as db:
        if filter_type == "all":
            cursor = await db.execute("SELECT id FROM users")
        else:
            cursor = await db.execute("SELECT DISTINCT user_id FROM service_requests WHERE status = 'active'")
        users = await cursor.fetchall()
    
    if not users:
        await message.answer("❌ هیچ کاربری برای ارسال وجود ندارد.")
        await state.clear()
        return
    
    sent = 0
    failed = 0
    await message.answer(f"⏳ در حال ارسال پیام به {len(users)} کاربر...")
    
    for user in users:
        try:
            await bot.send_message(user[0], text)
            sent += 1
        except:
            failed += 1
        await asyncio.sleep(0.05)
    
    await message.answer(
        f"✅ پیام گروهی ارسال شد!\n\n"
        f"📨 ارسال شده: {sent}\n"
        f"❌ ناموفق: {failed}"
    )
    await state.clear()

# ========== سیستم تخفیف - ایجاد کد توسط ادمین (FSM) ==========
@dp.message(DiscountStates.waiting_for_code)
async def discount_code_handler(message: Message, state: FSMContext):
    from admin import discount_process_code
    await discount_process_code(message, state)

@dp.callback_query(lambda c: c.data.startswith("discount_type_"))
async def discount_type_handler(callback: CallbackQuery, state: FSMContext):
    from admin import discount_process_type
    await discount_process_type(callback, state)

@dp.message(DiscountStates.waiting_for_value)
async def discount_value_handler(message: Message, state: FSMContext):
    from admin import discount_process_value
    await discount_process_value(message, state)

@dp.message(DiscountStates.waiting_for_max_uses)
async def discount_max_uses_handler(message: Message, state: FSMContext):
    from admin import discount_process_max_uses
    await discount_process_max_uses(message, state)

@dp.message(DiscountStates.waiting_for_days)
async def discount_days_handler(message: Message, state: FSMContext):
    from admin import discount_process_days
    await discount_process_days(message, state)

# ========== سیستم تخفیف - اعمال در خرید توسط کاربر (FSM) ==========
@dp.message(DiscountStates.waiting_for_discount_in_purchase)
async def process_discount_code_in_purchase(message: Message, state: FSMContext):
    if message.text.startswith("/"):
        await state.clear()
        await message.answer("❌ عملیات لغو شد.")
        return
    
    data = await state.get_data()
    user_id = data.get("user_id")
    original_price = data.get("price")
    volume = data.get("volume")
    plan_name = data.get("plan_name")
    
    result = await validate_discount_code(message.text, user_id)
    
    if not result["valid"]:
        await message.answer(result["message"])
        return
    
    new_price = await apply_discount(original_price, result["discount_type"], result["discount_value"])
    
    await state.update_data(
        discount_code=message.text.upper(),
        discount_code_id=result["code_id"],
        discount_type=result["discount_type"],
        discount_value=result["discount_value"],
        final_price=new_price
    )
    
    discount_text = f"{result['discount_value']}%" if result["discount_type"] == "percent" else f"{result['discount_value']:,} تومان"
    
    await message.answer(
        f"✅ کد تخفیف {message.text.upper()} اعمال شد!\n\n"
        f"💰 قیمت اصلی: {original_price:,} تومان\n"
        f"🎟 تخفیف: {discount_text}\n"
        f"💰 قیمت نهایی: {new_price:,} تومان\n\n"
        f"⏳ در حال بررسی موجودی..."
    )
    
    await process_purchase(message, state)

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
async def buy_callback(callback: CallbackQuery, state: FSMContext):
    await callback.answer("✅ در حال بررسی...")
    
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
    
    await state.update_data(
        price=price_int,
        volume=volume,
        plan_name=plan_name,
        user_id=user_id,
        final_price=price_int
    )
    
    keyboard = types.InlineKeyboardMarkup(inline_keyboard=[
        [types.InlineKeyboardButton(text="🎟 اعمال کد تخفیف", callback_data="apply_discount")],
        [types.InlineKeyboardButton(text="⏭ ادامه بدون تخفیف", callback_data="no_discount")]
    ])
    
    await callback.message.edit_text(
        f"🛒 تعرفه انتخاب شده:\n\n"
        f"📅 مدت: ۱ ماهه\n"
        f"📊 حجم: {volume}\n"
        f"💰 قیمت: {price_int:,} تومان\n\n"
        f"آیا کد تخفیف دارید؟",
        reply_markup=keyboard
    )

# ========== مدیریت دکمه‌های تخفیف در خرید ==========
@dp.callback_query(lambda c: c.data == "apply_discount")
async def apply_discount_callback(callback: CallbackQuery, state: FSMContext):
    await state.set_state(DiscountStates.waiting_for_discount_in_purchase)
    await callback.message.edit_text(
        "🎟 لطفاً کد تخفیف خود را وارد کنید:\n"
        "مثال: SUMMER10\n\n"
        "💡 برای انصراف، /cancel را وارد کنید."
    )
    await callback.answer()

@dp.callback_query(lambda c: c.data == "no_discount")
async def no_discount_callback(callback: CallbackQuery, state: FSMContext):
    await process_purchase(callback.message, state, callback=callback)

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
    await callback.message.edit_text(
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
            "SELECT user_id FROM service_requests WHERE id = ? AND status = 'active'",
            (request_id,)
        )
        result = await cursor.fetchone()
        
        if not result:
            await callback.message.edit_text("❌ این درخواست قبلاً پردازش شده.")
            await callback.answer()
            return
        
        user_id = result[0]
    
    await callback.message.edit_text(
        f"📤 لطفاً کانفیگ را برای کاربر {user_id} ارسال کن:\n\n"
        f"`/send {user_id} [متن کانفیگ]`"
    )
    await callback.answer()

# ========== مدیریت درخواست‌های شارژ (ادمین) ==========
@dp.callback_query(lambda c: c.data.startswith("approve_charge_") or c.data.startswith("reject_charge_"))
async def handle_charge_request(callback: CallbackQuery):
    await callback.answer("⏳ در حال پردازش...")
    
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی ندارید.", show_alert=True)
        return
    
    logger.info(f"📩 دریافت callback: {callback.data}")
    
    parts = callback.data.split("_")
    if len(parts) < 3:
        await callback.answer("❌ داده ناقص است.", show_alert=True)
        return
    
    action = parts[0]
    try:
        request_id = int(parts[2])
    except ValueError:
        await callback.answer("❌ شناسه نامعتبر است.", show_alert=True)
        return
    
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT user_id, amount FROM charge_requests WHERE id = ? AND status = 'pending'",
            (request_id,)
        )
        request = await cursor.fetchone()
        
        if not request:
            try:
                await callback.message.edit_text("❌ این درخواست قبلاً پردازش شده یا وجود ندارد.")
            except Exception as e:
                logger.warning(f"⚠️ خطا در ویرایش پیام: {e}")
                await callback.message.answer("❌ این درخواست قبلاً پردازش شده یا وجود ندارد.")
            await callback.answer()
            return
        
        user_id, amount = request
        logger.info(f"📝 درخواست {request_id}: کاربر {user_id} به مبلغ {amount} تومان")
        
        cursor = await db.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
        result = await cursor.fetchone()
        old_balance = result[0] if result else 0
        logger.info(f"💰 موجودی فعلی کاربر {user_id}: {old_balance} تومان")
        
        if action == "approve":
            try:
                await db.execute(
                    "UPDATE users SET balance = balance + ? WHERE id = ?",
                    (amount, user_id)
                )
                await db.execute(
                    "UPDATE charge_requests SET status = 'approved', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (request_id,)
                )
                await db.commit()
                logger.info(f"✅ کوئری‌ها با موفقیت اجرا و commit شدند.")
                
                cursor = await db.execute("SELECT balance FROM users WHERE id = ?", (user_id,))
                new_balance = (await cursor.fetchone())[0] or 0
                logger.info(f"💰 موجودی جدید کاربر {user_id}: {new_balance} تومان")
                
                try:
                    await bot.send_message(
                        user_id,
                        f"✅ درخواست شارژ شما به مبلغ {amount:,} تومان تأیید شد!\n"
                        f"💰 موجودی جدید شما: {new_balance:,} تومان"
                    )
                    logger.info(f"✅ پیام تأیید به کاربر {user_id} ارسال شد.")
                except Exception as e:
                    logger.error(f"❌ خطا در ارسال پیام به کاربر: {e}")
                
                try:
                    await callback.message.edit_text(
                        f"✅ درخواست {request_id} تأیید شد.\n"
                        f"👤 کاربر {user_id} به مبلغ {amount:,} تومان شارژ شد.\n"
                        f"💰 موجودی قبلی: {old_balance:,} تومان\n"
                        f"💰 موجودی جدید: {new_balance:,} تومان"
                    )
                    logger.info("✅ پیام ادمین ویرایش شد.")
                except TelegramBadRequest as e:
                    logger.warning(f"⚠️ خطا در ویرایش پیام (BadRequest): {e}")
                    await callback.message.answer(
                        f"✅ درخواست {request_id} تأیید شد.\n"
                        f"👤 کاربر {user_id} به مبلغ {amount:,} تومان شارژ شد.\n"
                        f"💰 موجودی قبلی: {old_balance:,} تومان\n"
                        f"💰 موجودی جدید: {new_balance:,} تومان"
                    )
                except Exception as e:
                    logger.error(f"❌ خطای غیرمنتظره در ویرایش: {e}")
                    await callback.message.answer(
                        f"✅ درخواست {request_id} تأیید شد.\n"
                        f"👤 کاربر {user_id} به مبلغ {amount:,} تومان شارژ شد."
                    )
                
            except Exception as e:
                logger.error(f"❌ خطا در تأیید درخواست: {e}")
                try:
                    await callback.message.edit_text(f"❌ خطا در تأیید درخواست:\n{str(e)}")
                except:
                    await callback.message.answer(f"❌ خطا در تأیید درخواست:\n{str(e)}")
                await callback.answer()
                return
        else:
            try:
                await db.execute(
                    "UPDATE charge_requests SET status = 'rejected', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                    (request_id,)
                )
                await db.commit()
                logger.info(f"✅ درخواست {request_id} رد شد.")
                
                try:
                    await bot.send_message(
                        user_id,
                        f"❌ درخواست شارژ شما به مبلغ {amount:,} تومان رد شد."
                    )
                    logger.info(f"✅ پیام رد به کاربر {user_id} ارسال شد.")
                except Exception as e:
                    logger.error(f"❌ خطا در ارسال پیام رد: {e}")
                
                try:
                    await callback.message.edit_text(f"❌ درخواست {request_id} رد شد.")
                except TelegramBadRequest:
                    await callback.message.answer(f"❌ درخواست {request_id} رد شد.")
                except Exception as e:
                    logger.error(f"❌ خطا در ویرایش پیام رد: {e}")
                    await callback.message.answer(f"❌ درخواست {request_id} رد شد.")
                
            except Exception as e:
                logger.error(f"❌ خطا در رد درخواست: {e}")
                try:
                    await callback.message.edit_text(f"❌ خطا در رد درخواست:\n{str(e)}")
                except:
                    await callback.message.answer(f"❌ خطا در رد درخواست:\n{str(e)}")
                await callback.answer()
                return
    
    await callback.answer("✅ عملیات با موفقیت انجام شد.")

# ========== مدیریت دکمه‌های پنل ادمین، تراکنش‌ها، تخفیف‌ها، برادکست و تنظیمات ==========
@dp.callback_query(lambda c: c.data and (
    c.data.startswith("admin_") or 
    c.data.startswith("trans_") or 
    c.data.startswith("broadcast_") or 
    c.data.startswith("discount_") or
    c.data.startswith("settings_")
))
async def admin_trans_callback(callback: CallbackQuery, state: FSMContext):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی ندارید.", show_alert=True)
        return
    
    # ========== مدیریت بخش ادمین ==========
    if callback.data.startswith("admin_"):
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
        elif callback.data == "admin_transactions":
            from admin import admin_transactions
            await admin_transactions(callback)
        elif callback.data == "admin_broadcast":
            from admin import admin_broadcast
            await admin_broadcast(callback, state)
        elif callback.data == "admin_discounts":
            from admin import admin_discounts
            await admin_discounts(callback)
        elif callback.data == "admin_settings":
            from admin import admin_settings
            await admin_settings(callback)
        else:
            await callback.answer("⏳ این بخش در حال توسعه است.", show_alert=True)
        return
    
    # ========== مدیریت تراکنش‌ها ==========
    if callback.data.startswith("trans_"):
        if callback.data == "trans_all":
            from admin import show_transactions
            await show_transactions(callback)
        elif callback.data == "trans_deposit":
            from admin import show_transactions
            await show_transactions(callback, trans_type="deposit")
        elif callback.data == "trans_purchase":
            from admin import show_transactions
            await show_transactions(callback, trans_type="purchase")
        elif callback.data == "trans_search_user":
            from admin import trans_search_user
            await trans_search_user(callback)
        else:
            await callback.answer("⏳ این بخش در حال توسعه است.", show_alert=True)
        return
    
    # ========== مدیریت ارسال پیام گروهی ==========
    if callback.data.startswith("broadcast_"):
        from admin import broadcast_to_users
        filter_type = callback.data.split("_")[1] if len(callback.data.split("_")) > 1 else "all"
        await broadcast_to_users(callback, state, filter_type)
        return
    
    # ========== مدیریت تخفیف‌ها ==========
    if callback.data.startswith("discount_"):
        if callback.data == "discount_create_simple":
            from admin import discount_create_simple
            await discount_create_simple(callback, state)
        elif callback.data == "discount_list":
            from admin import discount_list
            await discount_list(callback)
        else:
            await callback.answer("⏳ این بخش در حال توسعه است.", show_alert=True)
        return
    
    # ========== مدیریت تنظیمات ==========
    if callback.data.startswith("settings_"):
        from admin import settings_view, settings_min_charge, settings_welcome, settings_support, settings_plans
        from settings_manager import set_setting, get_setting
        
        if callback.data == "settings_view":
            await settings_view(callback)
        
        elif callback.data == "settings_min_charge":
            await settings_min_charge(callback)
            await state.set_state(SettingsStates.waiting_for_min_charge)
        
        elif callback.data == "settings_welcome":
            await settings_welcome(callback)
            await state.set_state(SettingsStates.waiting_for_welcome)
        
        elif callback.data == "settings_support":
            await settings_support(callback)
        
        elif callback.data == "settings_plans":
            await settings_plans(callback)
        
        elif callback.data == "settings_support_user":
            await callback.message.edit_text(
                "🆔 لطفاً نام کاربری ادمین جدید را وارد کنید:\n"
                "مثال: Dni2003"
            )
            await state.set_state(SettingsStates.waiting_for_support_user)
            await callback.answer()
        
        elif callback.data == "settings_support_hours":
            await callback.message.edit_text(
                "⏰ لطفاً ساعت پشتیبانی جدید را وارد کنید:\n"
                "مثال: ۸ صبح تا ۱۰ شب"
            )
            await state.set_state(SettingsStates.waiting_for_support_hours)
            await callback.answer()
        
        elif callback.data == "admin_settings":
            from admin import admin_settings
            await admin_settings(callback)
        
        else:
            await callback.answer("⏳ این بخش در حال توسعه است.", show_alert=True)

# ========== هندلرهای تنظیمات با FSM ==========
@dp.message(SettingsStates.waiting_for_min_charge)
async def settings_min_charge_process(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ شما دسترسی ندارید.")
        await state.clear()
        return
    
    try:
        amount = int(message.text)
        if amount < 10000:
            await message.answer("❌ حداقل مبلغ شارژ نباید کمتر از ۱۰,۰۰۰ تومان باشد.")
            return
        
        await set_setting("min_charge_amount", str(amount))
        await message.answer(f"✅ حداقل مبلغ شارژ به {amount:,} تومان تغییر یافت.")
        await state.clear()
        
    except ValueError:
        await message.answer("❌ لطفاً یک عدد معتبر وارد کنید.")

@dp.message(SettingsStates.waiting_for_welcome)
async def settings_welcome_process(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ شما دسترسی ندارید.")
        await state.clear()
        return
    
    await set_setting("welcome_message", message.text)
    await message.answer("✅ پیام خوش‌آمدگویی با موفقیت تغییر یافت.")
    await state.clear()

@dp.message(SettingsStates.waiting_for_support_user)
async def settings_support_user_process(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ شما دسترسی ندارید.")
        await state.clear()
        return
    
    username = message.text.replace("@", "").strip()
    await set_setting("support_username", username)
    await message.answer(f"✅ ادمین پشتیبانی به @{username} تغییر یافت.")
    await state.clear()

@dp.message(SettingsStates.waiting_for_support_hours)
async def settings_support_hours_process(message: Message, state: FSMContext):
    if not await is_admin(message.from_user.id):
        await message.answer("⛔ شما دسترسی ندارید.")
        await state.clear()
        return
    
    await set_setting("support_hours", message.text)
    await message.answer(f"✅ ساعت پشتیبانی به '{message.text}' تغییر یافت.")
    await state.clear()

# ========== اجرای اصلی ==========
async def main():
    try:
        await init_db()
        await check_and_update_expired()
        print("✅ دیتابیس راه‌اندازی شد!")
        print("🤖 ربات در حال اجراست...")
        await dp.start_polling(bot)
    except Exception as e:
        print(f"❌ خطا: {e}")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())
