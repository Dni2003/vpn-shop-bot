import aiosqlite
from config import config

DB_PATH = config.DATABASE_URL.replace("sqlite+aiosqlite:///", "")

async def admin_users(callback: types.CallbackQuery):
    try:
        async with aiosqlite.connect(DB_PATH) as db:  # مستقیم وصل شو
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
        await callback.message.edit_text(f"❌ خطا: {str(e)}")
        await callback.answer()

async def admin_stats(callback: types.CallbackQuery):
    try:
        async with aiosqlite.connect(DB_PATH) as db:  # مستقیم وصل شو
            cursor = await db.execute("SELECT COUNT(*) FROM users")
            total_users = (await cursor.fetchone())[0]
            
            cursor = await db.execute("SELECT SUM(amount) FROM transactions WHERE type='deposit' AND status='completed'")
            total_revenue = (await cursor.fetchone())[0] or 0
        
        text = f"📊 آمار کلی:\n\n"
        text += f"👥 کل کاربران: {total_users}\n"
        text += f"💰 کل فروش: {total_revenue:,} تومان"
        
        await callback.message.edit_text(text)
        await callback.answer()
    except Exception as e:
        await callback.message.edit_text(f"❌ خطا: {str(e)}")
        await callback.answer()
