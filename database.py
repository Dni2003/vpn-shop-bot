import aiosqlite
from config import config

# مسیر فایل دیتابیس
DB_PATH = config.DATABASE_URL.replace("sqlite+aiosqlite:///", "")

async def init_db():
    """ایجاد جدول‌ها (فقط یک بار اجرا می‌شود)"""
    async with aiosqlite.connect(DB_PATH) as db:
        # ========== جدول کاربران ==========
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
        
        # ========== جدول تراکنش‌ها ==========
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
        
        # ========== جدول کانفیگ‌های VPN ==========
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
        
        # ========== جدول درخواست‌های شارژ کیف پول ==========
        await db.execute("""
            CREATE TABLE IF NOT EXISTS charge_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                amount INTEGER,
                receipt_photo_id TEXT,
                status TEXT CHECK(status IN ('pending', 'approved', 'rejected')) DEFAULT 'pending',
                admin_note TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # ========== جدول سرویس‌ها (با ستون‌های انقضا) ==========
        await db.execute("""
            CREATE TABLE IF NOT EXISTS service_requests (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                plan_name TEXT,
                volume TEXT,
                price INTEGER,
                status TEXT CHECK(status IN ('pending', 'sent', 'expired', 'active')) DEFAULT 'pending',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                expires_at TIMESTAMP,
                notified BOOLEAN DEFAULT 0,
                FOREIGN KEY (user_id) REFERENCES users (id)
            )
        """)
        
        # ========== جدول کدهای تخفیف ==========
        await db.execute("""
            CREATE TABLE IF NOT EXISTS discount_codes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                code TEXT UNIQUE NOT NULL,
                discount_type TEXT CHECK(discount_type IN ('percent', 'fixed')),
                discount_value INTEGER NOT NULL,
                max_uses INTEGER DEFAULT 1,
                used_count INTEGER DEFAULT 0,
                expires_at TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                is_active BOOLEAN DEFAULT 1
            )
        """)
        
        # ========== جدول استفاده از تخفیف‌ها ==========
        await db.execute("""
            CREATE TABLE IF NOT EXISTS discount_usage (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                discount_code_id INTEGER,
                used_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (discount_code_id) REFERENCES discount_codes(id)
            )
        """)
        
        # ========== جدول تنظیمات ربات ==========
        await db.execute("""
            CREATE TABLE IF NOT EXISTS bot_settings (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                setting_key TEXT UNIQUE NOT NULL,
                setting_value TEXT,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # ========== درج تنظیمات پیش‌فرض ==========
        default_settings = [
            ("min_charge_amount", "100000"),
            ("welcome_message", "👋 سلام {first_name}!\nبه ربات خرید فیلترشکن خوش آمدید ❗️\nجهت خرید فیلترشکن از دکمه‌های زیر استفاده کنید:"),
            ("support_username", "Dni2003"),
            ("support_hours", "۹ صبح تا ۱۲ شب"),
            ("plans", "150000,239000,300000,339000,425000,540000,550000,840000"),
            ("plan_volumes", "20,28,50,53,75,90,100,213"),
        ]
        
        for key, value in default_settings:
            await db.execute(
                "INSERT OR IGNORE INTO bot_settings (setting_key, setting_value) VALUES (?, ?)",
                (key, value)
            )
        
        await db.commit()
        print("✅ تمام جدول‌های دیتابیس با موفقیت ایجاد/بررسی شدند.")

async def get_db():
    """هر بار یک اتصال جدید و تازه به دیتابیس برمی‌گرداند"""
    return await aiosqlite.connect(DB_PATH)
