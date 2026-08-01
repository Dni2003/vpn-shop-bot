import aiosqlite
from config import config

DB_PATH = config.DATABASE_URL.replace("sqlite+aiosqlite:///", "")

async def get_setting(key: str) -> str:
    """دریافت مقدار یک تنظیمات"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT setting_value FROM bot_settings WHERE setting_key = ?", (key,))
        result = await cursor.fetchone()
        return result[0] if result else None

async def set_setting(key: str, value: str) -> bool:
    """تنظیم مقدار یک تنظیمات"""
    try:
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute(
                "UPDATE bot_settings SET setting_value = ?, updated_at = CURRENT_TIMESTAMP WHERE setting_key = ?",
                (value, key)
            )
            await db.commit()
            return True
    except:
        return False

async def get_all_settings() -> dict:
    """دریافت همه تنظیمات"""
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("SELECT setting_key, setting_value FROM bot_settings")
        rows = await cursor.fetchall()
        return {row[0]: row[1] for row in rows}
