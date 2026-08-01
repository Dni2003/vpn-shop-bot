import aiosqlite
from config import config

DB_PATH = config.DATABASE_URL.replace("sqlite+aiosqlite:///", "")

async def save_admin_reply(admin_message_id: int, user_id: int):
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "INSERT INTO support_replies (admin_message_id, user_id) VALUES (?, ?)",
            (admin_message_id, user_id)
        )
        await db.commit()

async def get_user_by_admin_message(admin_message_id: int) -> int:
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT user_id FROM support_replies WHERE admin_message_id = ?",
            (admin_message_id,)
        )
        result = await cursor.fetchone()
        return result[0] if result else None
