import aiosqlite
from datetime import datetime
from config import config

DB_PATH = config.DATABASE_URL.replace("sqlite+aiosqlite:///", "")

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        # جدول کاربران
        await db.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                last_name TEXT,
                phone TEXT,
                balance INTEGER DEFAULT 0,
                registered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_admin BOOLEAN DEFAULT 0
            )
        """)
        
        # جدول تراکنش‌ها
        await db.execute("""
            CREATE TABLE IF NOT EXISTS transactions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                type TEXT CHECK(type IN ('deposit', 'withdraw', 'purchase')),
                description TEXT,
                status TEXT CHECK(status IN ('pending', 'completed', 'failed')) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # جدول کانفیگ‌های VPN
        await db.execute("""
            CREATE TABLE IF NOT EXISTS vpn_configs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                config_data TEXT NOT NULL,
                expires_at TIMESTAMP,
                is_active BOOLEAN DEFAULT 1,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        await db.commit()

async def get_db():
    return await aiosqlite.connect(DB_PATH)
