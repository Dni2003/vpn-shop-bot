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
        
        # ============================================================
        # 🔽 کدهای جدید را از اینجا اضافه کن 🔽
        # ============================================================
        
        # ========== جدول کدهای تخفیف (جدید) ==========
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
        
        # ========== جدول استفاده از تخفیف‌ها (جدید) ==========
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
        
        # ============================================================
        # 🔼 کدهای جدید تا اینجا 🔼
        # ============================================================
        
        await db.commit()
        print("✅ تمام جدول‌های دیتابیس با موفقیت ایجاد/بررسی شدند.")

async def get_db():
    """این تابع هر بار که صدا زده می‌شود، یک اتصال تازه و جدید به دیتابیس برمی‌گرداند.
    برای استفاده از آن حتماً باید از 'async with await get_db() as db' استفاده کنید.
    """
    return await aiosqlite.connect(DB_PATH)
