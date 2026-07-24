import random
import logging
from database import db

logger = logging.getLogger(__name__)

_A_CONFIG = {
    "humor_level": 8,
    "sarcasm_level": 6,
    "energy": 8,
    "street_language": 7,
    "creativity": 7,
    "label": "A — شوخ‌تر و پرانرژی",
}

_B_CONFIG = {
    "humor_level": 4,
    "sarcasm_level": 3,
    "energy": 5,
    "street_language": 4,
    "creativity": 5,
    "label": "B — هوشمندتر و آرام‌تر",
}


async def get_ab_group(chat_id: int) -> str:
    async with db.db.execute(
        "SELECT variant FROM ab_test WHERE chat_id = ?", (chat_id,)
    ) as cursor:
        row = await cursor.fetchone()
    if row:
        return row["variant"]
    variant = random.choice(["A", "B"])
    await db.db.execute(
        "INSERT INTO ab_test (chat_id, variant) VALUES (?, ?)", (chat_id, variant)
    )
    await db.db.commit()
    logger.info(f"Chat {chat_id} assigned to group {variant}")
    return variant


async def get_ab_config(chat_id: int) -> dict:
    group = await get_ab_group(chat_id)
    config = _A_CONFIG if group == "A" else _B_CONFIG
    return dict(config)


async def record_feedback(chat_id: int, user_id: int, variant: str, feedback_type: str):
    await db.db.execute(
        "INSERT INTO ab_feedback (chat_id, user_id, variant, feedback_type) VALUES (?, ?, ?, ?)",
        (chat_id, user_id, variant, feedback_type),
    )
    await db.db.commit()


async def get_ab_results() -> dict:
    async with db.db.execute("""
        SELECT variant, COUNT(*) as total,
               SUM(CASE WHEN feedback_type = 'positive' THEN 1 ELSE 0 END) as positive,
               SUM(CASE WHEN feedback_type = 'negative' THEN 1 ELSE 0 END) as negative
        FROM ab_feedback GROUP BY variant
    """) as cursor:
        rows = await cursor.fetchall()
    results = {}
    for r in rows:
        variant = r["variant"]
        total = r["total"] or 1
        results[variant] = {
            "total": r["total"],
            "positive": r["positive"] or 0,
            "negative": r["negative"] or 0,
            "satisfaction": round((r["positive"] or 0) / total * 100, 1),
        }
    return results
