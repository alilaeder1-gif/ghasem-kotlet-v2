import re
import logging

logger = logging.getLogger(__name__)

_CRITERIA_PATTERNS = {
    "personality": re.compile(
        r"(داداش|بابا|والا|راستش|دمت|کتلت|رفیق|حله|اختیار)", re.UNICODE
    ),
    "hallucination_markers": re.compile(
        r"(حتماً|دقیقاً|الزاماً|قطعاً|همیشه|همه|هیچ‌وقت)", re.UNICODE
    ),
    "fight": re.compile(
        r"(احمق|کثافت|گوه|فحش|کونی|جاکش)", re.UNICODE
    ),
}

_GOOD_LENGTH = (3, 70)

_BAD_MOODS = {"annoyed", "sad", "angry", "negative"}


async def judge_response(response: str, user_msg: str = "", user_emotion: str = "") -> dict:
    checks = {}

    # 1. Factual check (basic — no obvious hallucination markers + confidence)
    has_hallucination_markers = bool(_CRITERIA_PATTERNS["hallucination_markers"].search(response))
    checks["factual_ok"] = not has_hallucination_markers

    # 2. Personality check
    personality_score = 1 if _CRITERIA_PATTERNS["personality"].search(response) else 0
    checks["personality_ok"] = personality_score > 0

    # 3. Length check
    length = len(response)
    checks["length_ok"] = _GOOD_LENGTH[0] <= length <= _GOOD_LENGTH[1]

    # 4. Humor appropriateness
    has_laugh = bool(re.search(r"(😂|🤣|😁|خنده|جوک|شوخی|بامزه)", response))
    if user_emotion in _BAD_MOODS and has_laugh:
        checks["humor_ok"] = False
    else:
        checks["humor_ok"] = True

    # 5. Emotion understanding — basic empathy markers
    if user_emotion in _BAD_MOODS:
        has_empathy = bool(re.search(
            r"(ناراحت|متاسف|درد|احساس|غم|دلتنگ|تنها|سخته|می‌فهمم|حق با تو)",
            response, re.UNICODE,
        ))
        checks["emotion_ok"] = has_empathy
    else:
        checks["emotion_ok"] = True

    # 6. No conflict
    checks["no_conflict"] = not bool(_CRITERIA_PATTERNS["fight"].search(response))

    mandatory = ["factual_ok", "hallucination_markers"]
    mandatory_pass = all(checks.get(m, True) for m in mandatory)
    total_pass = sum(1 for v in checks.values() if v)
    checks["passed"] = mandatory_pass and (total_pass >= 4)
    checks["score"] = total_pass / len(checks)

    logger.debug(f"Judge: {checks}")
    return checks


async def needs_judge(response: str) -> bool:
    if len(response) < 3:
        return True
    if response.startswith(("⚠", "⏳")):
        return False
    fast_pass = bool(re.search(
        r"^(س+ل+ا*م*|درود|خوبی|چطوری|حله|باشه|چشم)",
        response, re.IGNORECASE,
    ))
    return not fast_pass
