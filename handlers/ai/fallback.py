from aiogram import Router, F
from aiogram.types import Message
from database import db

router = Router()


async def get_fallback_answer(text: str) -> str | None:
    text_lower = text.lower().strip()

    # Pattern replies
    patterns = {
        "سلام": "سلام داداش! چطوری؟ 😎",
        "خوبی": "خوبم داداش! تو چطوری؟ 🤙",
        "چطوری": "دمت گرم! من کتلت‌م همیشه آماده 🤖",
        "خداحافظ": "فعلاً... هر وقت needed باشی من هستم! 🙌",
        "ممنون": "خواهش می‌کنم داداش! 🫡",
        "مرسی": "قربانت داداش! 🫡",
        "داداش": "جانم! چیزیم می‌خوای؟ 😄",
        "کتلت": "جانم! بفرما چی کار داری؟ 🤖",
    }
    for keyword, reply in patterns.items():
        if keyword in text_lower:
            return reply

    # Message database fallback
    try:
        results = await db.search_similar_qa(0, text, limit=1)
        if results:
            return results[0]["answer"]
    except:
        pass

    return None
