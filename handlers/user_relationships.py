import logging
from database import db

logger = logging.getLogger(__name__)

_DEFAULT_RELATION = {
    "preferred_name": "",
    "speaking_style": "default",
    "humor_preference": 5,
    "technical_level": 5,
    "interaction_mood": "neutral",
    "last_topic": "",
    "total_interactions": 0,
}


async def get_relationship(user_id: int, chat_id: int) -> dict:
    async with db.db.execute(
        "SELECT * FROM user_relationships WHERE user_id = ? AND chat_id = ?",
        (user_id, chat_id),
    ) as cursor:
        row = await cursor.fetchone()
    if row:
        return dict(row)
    return dict(_DEFAULT_RELATION)


async def update_relationship(user_id: int, chat_id: int, **kwargs):
    existing = await get_relationship(user_id, chat_id)
    if existing.get("user_id") is None:
        await db.db.execute(
            "INSERT INTO user_relationships (user_id, chat_id) VALUES (?, ?)",
            (user_id, chat_id),
        )
    cols = ", ".join(f"{k} = ?" for k in kwargs)
    vals = list(kwargs.values()) + [user_id, chat_id]
    await db.db.execute(
        f"UPDATE user_relationships SET {cols}, last_seen = datetime('now') WHERE user_id = ? AND chat_id = ?",
        vals,
    )
    await db.db.commit()


async def track_interaction(user_id: int, chat_id: int, topic: str = ""):
    existing = await get_relationship(user_id, chat_id)
    total = (existing.get("total_interactions") or 0) + 1
    kwargs = {"total_interactions": total}
    if topic:
        kwargs["last_topic"] = topic[:200]
    await update_relationship(user_id, chat_id, **kwargs)


async def detect_speaking_style(text: str) -> str:
    import re
    formal = re.search(r"(می‌فرمایید|بفرمایید|تشکر|استخدام|معذور)", text)
    slang = re.search(r"(بابا|داداش|حله|دیگه|نکنه|بیا|برو)", text)
    technical = re.search(r"(API|سرور|کد|دیتابیس|الگوریتم|فانکشن|متغیر)", text, re.IGNORECASE)
    if technical:
        return "technical"
    if formal:
        return "formal"
    if slang:
        return "slang"
    return "default"


async def detect_humor_preference(text: str) -> int:
    import re
    laugh = re.search(r"(😂|🤣|😁|خنده|شوخی|بامزه|جوک)", text)
    serious_markers = re.search(r"(دقیق|جدی|علمی|مستند|آمار)", text)
    if laugh:
        return 8
    if serious_markers:
        return 3
    return 5


async def detect_mood(text: str) -> str:
    import re
    if re.search(r"(😡|🤬|عصب|خشم|کثافت|بی‌ادب)", text):
        return "angry"
    if re.search(r"(😢|😭|غمگین|افسرد|دلم گرفته|بدبخت)", text):
        return "negative"
    if re.search(r"(😊|😂|خوشحال|عالی|دمت|قشنگ)", text):
        return "positive"
    return "neutral"
