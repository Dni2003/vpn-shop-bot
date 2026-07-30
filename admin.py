from aiogram import types
from aiogram.filters import Command
from aiogram.types import Message
from config import config
from database import get_db

# بررسی اینکه کاربر ادمین هست یا نه
async def is_admin(user_id: int) -> bool:
    return user_id in config.ADMIN_IDS

# دستور /admin
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

# دریافت لیست کاربران
async def admin_users(callback: types.CallbackQuery):
    async with get_db() as db:
        cursor = await db.execute("SELECT id, username, first_name, balance FROM users LIMIT 10")
        users = await cursor.fetchall()
    
    text = "👥 لیست کاربران:\n\n"
    for user in users:
        text += f"🆔 {user[0]} | {user[1] or 'بدون نام کاربری'} | موجودی: {user[3]} تومان\n"
    
    await callback.message.edit_text(text)
    await callback.answer()

# دریافت آمار
async def admin_stats(callback: types.CallbackQuery):
    async with get_db() as db:
        cursor = await db.execute("SELECT COUNT(*) FROM users")
        total_users = (await cursor.fetchone())[0]
        
        cursor = await db.execute("SELECT SUM(amount) FROM transactions WHERE type='deposit' AND status='completed'")
        total_revenue = (await cursor.fetchone())[0] or 0
    
    text = f"📊 آمار کلی:\n\n"
    text += f"👥 کل کاربران: {total_users}\n"
    text += f"💰 کل فروش: {total_revenue:,} تومان"
    
    await callback.message.edit_text(text)
    await callback.answer()

# شارژ کاربر
async def admin_add_balance(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "💰 لطفاً آیدی کاربر و مبلغ شارژ رو وارد کن:\n"
        "مثال: /add_balance 123456789 50000"
    )
    await callback.answer()
