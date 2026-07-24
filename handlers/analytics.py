import logging
from datetime import datetime
from database import db

logger = logging.getLogger(__name__)


async def log_conversation(
    chat_id: int,
    user_id: int,
    user_message: str,
    bot_response: str,
    emotion: str = "",
    humor_used: bool = False,
    hallucination_risky: bool = False,
    quality_score: float = 1.0,
    passed_gate: bool = True,
):
    await db.db.execute(
        """INSERT INTO chat_analytics
           (chat_id, user_id, user_message, bot_response, response_length,
            emotion_detected, humor_used, hallucination_risky, quality_score, passed_quality_gate)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            chat_id,
            user_id,
            user_message[:300],
            bot_response[:300],
            len(bot_response),
            emotion,
            int(humor_used),
            int(hallucination_risky),
            quality_score,
            int(passed_gate),
        ),
    )
    await db.db.commit()


async def get_daily_report(chat_id: int = None) -> dict:
    today = datetime.now().strftime("%Y-%m-%d")
    if chat_id:
        rows_c = await db.db.execute(
            "SELECT COUNT(*) as c FROM chat_analytics WHERE date(created_at) = ? AND chat_id = ?",
            (today, chat_id),
        )
    else:
        rows_c = await db.db.execute(
            "SELECT COUNT(*) as c FROM chat_analytics WHERE date(created_at) = ?",
            (today,),
        )
    row = await rows_c.fetchone()
    total = row["c"] if row else 0
    return {
        "date": today,
        "total_messages": total,
    }


async def get_summary(days: int = 7) -> dict:
    from datetime import datetime, timedelta
    since = (datetime.now() - timedelta(days=days)).isoformat()
    async with db.db.execute(
        """SELECT
            COUNT(*) as total,
            AVG(response_length) as avg_len,
            SUM(humor_used) as humor_count,
            SUM(hallucination_risky) as hallucination_count,
            AVG(quality_score) as avg_quality,
            1.0 * SUM(passed_quality_gate) / COUNT(*) as pass_rate
           FROM chat_analytics WHERE created_at >= ?""",
        (since,),
    ) as cursor:
        row = await cursor.fetchone()
    if not row or row["total"] == 0:
        return {"total": 0}
    return {
        "total_messages": row["total"],
        "avg_response_length": round(row["avg_len"] or 0, 1),
        "humor_count": row["humor_count"] or 0,
        "hallucination_risky": row["hallucination_count"] or 0,
        "avg_quality": round(row["avg_quality"] or 0, 2),
        "quality_pass_rate": round((row["pass_rate"] or 0) * 100, 1),
        "period_days": days,
    }
