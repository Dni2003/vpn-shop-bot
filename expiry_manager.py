import aiosqlite
from datetime import datetime, timedelta
from config import config

DB_PATH = config.DATABASE_URL.replace("sqlite+aiosqlite:///", "")

async def check_and_update_expired():
    """بررسی سرویس‌های منقضی‌شده و به‌روزرسانی وضعیت"""
    async with aiosqlite.connect(DB_PATH) as db:
        now = datetime.now().isoformat()
        
        # پیدا کردن سرویس‌های منقضی‌شده که هنوز expired نشدن
        await db.execute(
            "UPDATE service_requests SET status = 'expired' WHERE status = 'active' AND expires_at < ?",
            (now,)
        )
        await db.commit()

async def get_user_active_service(user_id: int):
    """دریافت سرویس فعال کاربر"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT plan_name, volume, expires_at FROM service_requests WHERE user_id = ? AND status = 'active' ORDER BY created_at DESC LIMIT 1",
            (user_id,)
        )
        return await cursor.fetchone()

async def get_users_expiring_soon(days=3):
    """دریافت کاربرانی که سرویسشون در days روز آینده منقضی میشه"""
    now = datetime.now()
    target_date = now + timedelta(days=days)
    
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT user_id, plan_name, expires_at FROM service_requests WHERE status = 'active' AND expires_at BETWEEN ? AND ? AND notified = 0",
            (now.isoformat(), target_date.isoformat())
        )
        return await cursor.fetchall()

async def mark_notified(user_id: int):
    """علامت‌گذاری اخطار ارسال شده"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE service_requests SET notified = 1 WHERE user_id = ? AND status = 'active'",
            (user_id,)
        )
        await db.commit()
