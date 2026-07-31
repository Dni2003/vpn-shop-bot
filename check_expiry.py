import asyncio
from datetime import datetime
from aiogram import Bot
from expiry_manager import get_users_expiring_soon, mark_notified

async def send_expiry_warnings(bot: Bot):
    """ارسال اخطار به کاربرانی که سرویسشون در حال انقضاست"""
    users = await get_users_expiring_soon(days=3)
    
    for user_id, plan_name, expires_at in users:
        try:
            await bot.send_message(
                user_id,
                f"⚠️ یادآوری: سرویس {plan_name} شما در ۳ روز دیگر منقضی می‌شود.\n"
                f"برای تمدید، به بخش خرید اشتراک بروید."
            )
            await mark_notified(user_id)
        except:
            pass
