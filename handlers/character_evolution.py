import logging
from database import db

logger = logging.getLogger(__name__)


async def record_usage(phrase: str, category: str, success: bool = True):
    async with db.db.execute(
        "SELECT id, success_count, fail_count FROM character_evolution WHERE phrase = ? AND category = ?",
        (phrase, category),
    ) as cursor:
        row = await cursor.fetchone()
    if row:
        if success:
            await db.db.execute(
                "UPDATE character_evolution SET success_count = success_count + 1, last_used = datetime('now') WHERE id = ?",
                (row["id"],),
            )
        else:
            await db.db.execute(
                "UPDATE character_evolution SET fail_count = fail_count + 1, last_used = datetime('now') WHERE id = ?",
                (row["id"],),
            )
    else:
        await db.db.execute(
            "INSERT INTO character_evolution (phrase, category, success_count, fail_count, last_used) VALUES (?, ?, ?, ?, datetime('now'))",
            (phrase, category, 1 if success else 0, 0 if success else 1),
        )
    await db.db.commit()


async def get_phrase_score(phrase: str, category: str) -> float:
    async with db.db.execute(
        "SELECT success_count, fail_count FROM character_evolution WHERE phrase = ? AND category = ?",
        (phrase, category),
    ) as cursor:
        row = await cursor.fetchone()
    if not row:
        return 0.5
    total = row["success_count"] + row["fail_count"]
    if total == 0:
        return 0.5
    return row["success_count"] / total


async def get_overused_phrases(category: str = None, min_uses: int = 5) -> list:
    q = "SELECT phrase, success_count, fail_count FROM character_evolution"
    params = []
    if category:
        q += " WHERE category = ?"
        params.append(category)
    q += " ORDER BY (success_count + fail_count) DESC LIMIT 10"
    async with db.db.execute(q, params) as cursor:
        rows = await cursor.fetchall()
    result = []
    for r in rows:
        total = r["success_count"] + r["fail_count"]
        if total >= min_uses:
            result.append({
                "phrase": r["phrase"],
                "success_count": r["success_count"],
                "fail_count": r["fail_count"],
                "score": r["success_count"] / total,
                "total_uses": total,
            })
    return result


async def get_top_performers(category: str = None, limit: int = 5) -> list:
    q = "SELECT phrase, category, success_count, fail_count FROM character_evolution"
    params = []
    if category:
        q += " WHERE category = ?"
        params.append(category)
    q += " ORDER BY (success_count * 1.0 / MAX(success_count + fail_count, 1)) DESC, success_count DESC LIMIT ?"
    params.append(limit)
    async with db.db.execute(q, params) as cursor:
        rows = await cursor.fetchall()
    return [dict(r) for r in rows]
