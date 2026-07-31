import asyncio
import logging
import sys
import aiosqlite
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.types import Message, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.exceptions import TelegramBadRequest  # <-- اضافه شد

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

# ... (بقیه کدها مثل قبل) ...

# ========== مدیریت درخواست‌های شارژ (ادمین) ==========
@dp.callback_query(lambda c: c.data.startswith("approve_charge_") or c.data.startswith("reject_charge_"))
async def handle_charge_request(callback: CallbackQuery):
    if not await is_admin(callback.from_user.id):
        await callback.answer("⛔ شما دسترسی ندارید.", show_alert=True)
        return
    
    parts = callback.data.split("_")
    action = parts[0]
    request_id = int(parts[2])
    
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT user_id, amount FROM charge_requests WHERE id = ? AND status = 'pending'",
            (request_id,)
        )
        request = await cursor.fetchone()
        
        if not request:
            try:
                await callback.message.edit_text("❌ این درخواست قبلاً پردازش شده یا وجود ندارد.")
            except TelegramBadRequest:
                await callback.message.answer("❌ این درخواست قبلاً پردازش شده یا وجود ندارد.")
            await callback.answer()
            return
        
        user_id, amount = request
        
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
                
                try:
                    await bot.send_message(
                        user_id,
                        f"✅ درخواست شارژ شما به مبلغ {amount:,} تومان تأیید شد!\n"
                        f"💰 موجودی شما افزایش یافت."
                    )
                except:
                    pass
                
                try:
                    await callback.message.edit_text(
                        f"✅ درخواست {request_id} تأیید شد.\n"
                        f"👤 کاربر {user_id} به مبلغ {amount:,} تومان شارژ شد."
                    )
                except TelegramBadRequest:
                    await callback.message.answer(
                        f"✅ درخواست {request_id} تأیید شد.\n"
                        f"👤 کاربر {user_id} به مبلغ {amount:,} تومان شارژ شد."
                    )
                
            except Exception as e:
                try:
                    await callback.message.edit_text(f"❌ خطا در تأیید درخواست:\n{str(e)}")
                except TelegramBadRequest:
                    await callback.message.answer(f"❌ خطا در تأیید درخواست:\n{str(e)}")
                await callback.answer()
                return
        else:
            await db.execute(
                "UPDATE charge_requests SET status = 'rejected', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
                (request_id,)
            )
            await db.commit()
            
            try:
                await bot.send_message(
                    user_id,
                    f"❌ درخواست شارژ شما به مبلغ {amount:,} تومان رد شد."
                )
            except:
                pass
            
            try:
                await callback.message.edit_text(
                    f"❌ درخواست {request_id} رد شد.\n"
                    f"👤 کاربر {user_id} از شارژ {amount:,} تومانی محروم شد."
                )
            except TelegramBadRequest:
                await callback.message.answer(
                    f"❌ درخواست {request_id} رد شد.\n"
                    f"👤 کاربر {user_id} از شارژ {amount:,} تومانی محروم شد."
                )
    
    await callback.answer()

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
