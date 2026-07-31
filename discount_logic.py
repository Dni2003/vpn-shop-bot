import aiosqlite
from datetime import datetime
from config import config

DB_PATH = config.DATABASE_URL.replace("sqlite+aiosqlite:///", "")

async def validate_discount_code(code: str, user_id: int) -> dict:
    """
    بررسی اعتبار کد تخفیف
    
    Returns:
        {
            "valid": True/False,
            "discount_type": "percent" / "fixed",
            "discount_value": int,
            "message": str,
            "code_id": int
        }
    """
    code = code.upper().strip()
    
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT id, discount_type, discount_value, max_uses, used_count, expires_at, is_active FROM discount_codes WHERE code = ?",
            (code,)
        )
        result = await cursor.fetchone()
        
        if not result:
            return {"valid": False, "message": "❌ کد تخفیف نامعتبر است."}
        
        code_id, d_type, d_value, max_uses, used_count, expires_at, is_active = result
        
        # بررسی فعال بودن
        if not is_active:
            return {"valid": False, "message": "❌ این کد تخفیف غیرفعال شده است."}
        
        # بررسی تعداد استفاده
        if used_count >= max_uses:
            return {"valid": False, "message": "❌ این کد تخفیف به پایان رسیده است."}
        
        # بررسی انقضا
        if expires_at:
            expire_date = datetime.fromisoformat(expires_at)
            if datetime.now() > expire_date:
                return {"valid": False, "message": "❌ این کد تخفیف منقضی شده است."}
        
        # بررسی اینکه کاربر قبلاً از این کد استفاده کرده
        cursor = await db.execute(
            "SELECT id FROM discount_usage WHERE user_id = ? AND discount_code_id = ?",
            (user_id, code_id)
        )
        if await cursor.fetchone():
            return {"valid": False, "message": "❌ شما قبلاً از این کد تخفیف استفاده کرده‌اید."}
        
        return {
            "valid": True,
            "discount_type": d_type,
            "discount_value": d_value,
            "message": "✅ کد تخفیف معتبر است!",
            "code_id": code_id
        }

async def apply_discount(price: int, discount_type: str, discount_value: int) -> int:
    """اعمال تخفیف بر روی قیمت"""
    if discount_type == "percent":
        new_price = price - int(price * discount_value / 100)
    else:  # fixed
        new_price = max(0, price - discount_value)
    return new_price

async def mark_discount_used(code_id: int, user_id: int):
    """ثبت استفاده از کد تخفیف"""
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "UPDATE discount_codes SET used_count = used_count + 1 WHERE id = ?",
            (code_id,)
        )
        await db.execute(
            "INSERT INTO discount_usage (user_id, discount_code_id) VALUES (?, ?)",
            (user_id, code_id)
        )
        await db.commit()
