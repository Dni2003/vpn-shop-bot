import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    BOT_TOKEN = os.getenv("BOT_TOKEN")
    ADMIN_IDS = list(map(int, os.getenv("ADMIN_IDS", "").split(","))) if os.getenv("ADMIN_IDS") else []
    DATABASE_URL = os.getenv("DATABASE_URL", "sqlite+aiosqlite:///database.db")
    CARD_NUMBER = os.getenv("CARD_NUMBER", "6219861801306746 دانیال بدری")
    # تنظیمات مالی
    CURRENCY = "IRR"  # یا "USD"
    VAT_PERCENT = 0  # درصد مالیات
    
    @classmethod
    def validate(cls):
        if not cls.BOT_TOKEN:
            raise ValueError("BOT_TOKEN not set in environment variables")
        return True

config = Config()
