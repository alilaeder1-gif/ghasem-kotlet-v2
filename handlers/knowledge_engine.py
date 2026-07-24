import re
import logging
from database import db
from cache import cache

logger = logging.getLogger(__name__)

_LEVEL1_FAQ = {
    "سلام": "سلام داداش! چطوری؟ 😎",
    "خداحافظ": "فعلاً... بعداً می‌بینمت! 🤙",
    "کمک": "چیزی می‌خوای؟ منو صدا زدی بگو! 🤖",
    "قوانین": "قوانین گروه رو ادمین تعیین کرده، اگه سوالی داری بپرس.",
    "چطوری": "دمتم گرم داداش! فقط دارم کم کم کُتلت می‌شم 😂",
    "کتی": "جان داداش؟ ☺️",
    "کتلت": "جانم؟ بفرما! 😎",
    "قاسم": "جانم؟ بفرما! 😎",
}

_PERSIAN_WORDS = re.compile(r'[\wآ-ی]+', re.UNICODE)


def _tokenize(text: str) -> set[str]:
    return set(_PERSIAN_WORDS.findall(text.lower()))


def _jaccard_sim(a: set, b: set) -> float:
    if not a or not b: return 0
    return len(a & b) / len(a | b)


def _get_keywords(text: str) -> str:
    return " ".join(_PERSIAN_WORDS.findall(text.lower()))[:200]


async def check_level1(text: str) -> str | None:
    clean = text.strip().lower()
    for keyword, answer in _LEVEL1_FAQ.items():
        if keyword in clean:
            return answer
    return None


async def check_level2(text: str, chat_id: int = None) -> tuple[str | None, int | None]:
    results = await db.search_knowledge(text, threshold=0.3)
    if not results:
        return None, None
    best = results[0]
    words_q = _tokenize(text)
    words_best = _tokenize(best["question"])
    sim = _jaccard_sim(words_q, words_best)
    if sim >= 0.25:
        await db.increment_knowledge_usage(best["id"])
        return best["answer"], best["id"]
    if results and len(results) > 1:
        for r in results[1:]:
            words_r = _tokenize(r["question"])
            if _jaccard_sim(words_q, words_r) >= 0.25:
                await db.increment_knowledge_usage(r["id"])
                return r["answer"], r["id"]
    return None, None


async def evaluate_quality(question: str, answer: str) -> float:
    score = 3.0
    if len(answer) < 10: score -= 1
    if len(answer) > 20: score += 0.5
    if len(answer) > 60: score += 0.5
    if answer.startswith(("⚠", "⏳", "❌")): score -= 2
    if any(w in answer.lower() for w in ["داداش", "جانم", "دمت"]): score += 0.5
    persian_chars = sum(1 for c in answer if '\u0600' <= c <= '\u06FF')
    if persian_chars < 3: score -= 1
    if persian_chars > 10: score += 0.5
    return max(1, min(5, score))


async def save_quality_response(question: str, answer: str, source: str = "ai"):
    quality = await evaluate_quality(question, answer)
    if quality >= 3.5:
        keywords = _get_keywords(question)
        await db.add_knowledge(question, answer, keywords, quality, source)


async def hybrid_answer(text: str, chat_id: int = None) -> str | None:
    cached = await cache.get(f"kb:{text[:50]}")
    if cached:
        return cached

    l1 = await check_level1(text)
    if l1:
        await cache.set(f"kb:{text[:50]}", l1, ttl=3600)
        return l1

    l2, kid = await check_level2(text, chat_id)
    if l2:
        await cache.set(f"kb:{text[:50]}", l2, ttl=3600)
        return l2

    return None


async def hybrid_flow(text: str, chat_id: int, user_id: int, ai_coro, context: dict = None) -> str:
    kb_answer = await hybrid_answer(text, chat_id)
    if kb_answer:
        return kb_answer

    try:
        response = await ai_coro
        if response and not response.startswith(("⚠", "⏳", "❌")):
            await save_quality_response(text, response)
            await db.save_qa_pair(chat_id, user_id, text, response)
            return response
        return fallback_message(text)
    except Exception as e:
        logger.warning(f"AI failed, using fallback: {e}")
        return fallback_message(text)


def fallback_message(text: str) -> str:
    words = _PERSIAN_WORDS.findall(text.lower())
    if any(w in text.lower() for w in ["کی", "کیا", "کیه", "کی هست"]):
        return "🤖 هوش مصنوعی فعلاً در دسترس نیست. سؤال تو ثبت شد، بعداً جواب می‌دم."
    if any(w in text.lower() for w in ["کجاست", "کجایی", "کجا"]):
        return "🤖 الان نمی‌تونم جواب بدم. هوش مصنوعی موقتاً قطع شده."
    return "🤖 هوش مصنوعی موقتاً در دسترس نیست. سؤال تو ثبت شد و بعداً بررسی می‌شه."
