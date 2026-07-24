import re
import time
import logging
from database import db
from cache import cache

logger = logging.getLogger(__name__)

_PERSIAN_WORDS = re.compile(r'[\wآ-ی]+', re.UNICODE)
_OFFLINE_CACHE: list[dict] = []
_LAST_LOAD: float = 0


async def _load_offline():
    global _OFFLINE_CACHE, _LAST_LOAD
    now = time.time()
    if now - _LAST_LOAD > 60:
        _OFFLINE_CACHE = await db.get_all_offline_answers()
        _LAST_LOAD = now


def _normalize(text: str) -> str:
    text = text.lower().strip()
    text = text.replace("\u200c", " ").replace("\u200d", "")
    text = re.sub(r'[^\wآ-ی\s]', '', text)
    text = re.sub(r'\s+', ' ', text).strip()
    return text


def _tokenize(text: str) -> set[str]:
    return set(_PERSIAN_WORDS.findall(text.lower()))


def _jaccard_sim(a: set, b: set) -> float:
    if not a or not b: return 0
    return len(a & b) / len(a | b)


def _get_keywords(text: str) -> str:
    return " ".join(_PERSIAN_WORDS.findall(text.lower()))[:200]


async def check_offline(text: str) -> str | None:
    await _load_offline()
    clean = _normalize(text)
    for entry in _OFFLINE_CACHE:
        triggers = [t.strip() for t in entry["triggers"].split(",")]
        for trigger in triggers:
            t = _normalize(trigger)
            if t and t in clean:
                return entry["answer"]
    return None


async def check_level2(text: str) -> tuple[str | None, int | None]:
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


async def hybrid_answer(text: str) -> tuple[str | None, str]:
    # Layer 0: Redis cache
    cached = await cache.get(f"kb:{text[:50]}")
    if cached:
        return cached, "cache"

    # Layer 0b: SQLite persistent cache
    sql_cached = await db.cache_qa_has(text)
    if sql_cached:
        await cache.set(f"kb:{text[:50]}", sql_cached, ttl=3600)
        return sql_cached, "cache"

    # Layer 1: Offline answers (keyword match)
    offline = await check_offline(text)
    if offline:
        await cache.set(f"kb:{text[:50]}", offline, ttl=3600)
        await db.cache_qa_set(text, offline)
        return offline, "offline"

    # Layer 2: Knowledge Base (Jaccard similarity)
    l2, kid = await check_level2(text)
    if l2:
        await cache.set(f"kb:{text[:50]}", l2, ttl=3600)
        await db.cache_qa_set(text, l2)
        return l2, "kb"

    # Layer 3: AI Intent Classification (no text generation)
    try:
        from handlers.intent_engine import classify
        intent = await classify(text, use_ai=True)
        if intent.get("confidence", 0) >= 0.5 and intent.get("intent_name") not in ("unknown", ""):
            answer = await db.get_offline_answer_by_intent(intent["intent_name"])
            if answer:
                await cache.set(f"kb:{text[:50]}", answer, ttl=3600)
                await db.cache_qa_set(text, answer)
                return answer, "intent"
            # Try by intent_id
            iid = intent.get("intent_id", 0)
            if iid:
                answer = await db.get_offline_answer_by_intent_id(iid)
                if answer:
                    await cache.set(f"kb:{text[:50]}", answer, ttl=3600)
                    await db.cache_qa_set(text, answer)
                    return answer, "intent"
    except Exception as e:
        logger.debug(f"AI intent layer failed: {e}")

    return None, "miss"


async def hybrid_flow(text: str, chat_id: int, user_id: int, ai_coro) -> str:
    kb_answer, source = await hybrid_answer(text)
    if kb_answer:
        await db.log_ai_request(user_id, text, kb_answer, source, 0, source)
        return kb_answer

    # Nothing matched — queue as unanswered for admin review
    try:
        await db.add_unanswered(text, user_id, chat_id)
        logger.info(f"Unanswered queued: {text[:60]}")
    except Exception as e:
        logger.warning(f"Failed to queue unanswered: {e}")

    # Still try AI text generation as a last resort (may be removed later)
    import time as _time
    t0 = _time.time()
    try:
        response = await ai_coro
        latency = _time.time() - t0
        if response and not response.startswith(("⚠", "⏳", "❌")):
            await db.cache_qa_set(text, response)
            await save_quality_response(text, response)
            await db.save_qa_pair(chat_id, user_id, text, response)
            await db.increment_user_ai_usage(user_id)
            await db.log_ai_request(user_id, text, response, "ai_pool", latency, "ai")
            return response
        await db.log_ai_request(user_id, text, response or "", "fallback", latency, "offline")
        return fallback_message(text)
    except Exception as e:
        latency = _time.time() - t0
        logger.warning(f"AI failed, using fallback: {e}")
        await db.log_ai_request(user_id, text, str(e)[:100], "error", latency, "offline")
        return fallback_message(text)


def clear_cache():
    global _OFFLINE_CACHE, _LAST_LOAD
    _OFFLINE_CACHE.clear()
    _LAST_LOAD = 0


def fallback_message(text: str) -> str:
    if any(w in text.lower() for w in ["کی", "کیا", "کیه", "کی هست"]):
        return "❌ هوش مصنوعی فعلاً در دسترس نیست. سؤال تو ثبت شد، بعداً جواب می‌دم."
    if any(w in text.lower() for w in ["کجاست", "کجایی", "کجا"]):
        return "❌ الان نمی‌تونم جواب بدم. هوش مصنوعی موقتاً قطع شده."
    return "❌ هوش مصنوعی موقتاً در دسترس نیست. لطفاً چند دقیقه دیگر دوباره امتحان کنید."
