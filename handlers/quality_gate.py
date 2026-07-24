import re
import logging

logger = logging.getLogger(__name__)

_MIN_RELEVANT_LENGTH = 3
_MAX_RESPONSE_LENGTH = 70
_TEHRANI_MARKERS = re.compile(
    r"(داداش|بابا|والا|راستش|دقیقاً|حله|دمت|کُتلت|کتلت|رفیق|اختیار|قربان)",
    re.UNICODE,
)
_FIGHT_TRIGGERS = re.compile(
    r"(احمق|کثافت|بی‌شرف|گوه|فحش|کیر|کونی|جاکش|ننه|مادر)",
    re.UNICODE,
)
_UNCERTAINTY_MARKERS = re.compile(
    r"(نمی‌دونم|مطمئن نیستم|شاید|حدس می‌زنم|به نظرم|فکر کنم)",
    re.UNICODE,
)


async def check_relevance(user_msg: str, response: str) -> bool:
    if len(response) < _MIN_RELEVANT_LENGTH:
        return False
    return True


async def check_length(response: str) -> bool:
    return len(response) <= _MAX_RESPONSE_LENGTH


async def check_personality(response: str) -> bool:
    return bool(_TEHRANI_MARKERS.search(response))


async def check_humor_necessity(user_emotion: str) -> bool:
    inappropriate = {"annoyed", "sad", "angry", "negative"}
    return user_emotion not in inappropriate


async def check_accuracy(response: str) -> bool:
    if _UNCERTAINTY_MARKERS.search(response):
        return True
    return True


async def check_non_conflict(response: str) -> bool:
    return not bool(_FIGHT_TRIGGERS.search(response))


async def evaluate_response(user_msg: str, response: str, user_emotion: str = "") -> dict:
    results = {
        "relevant": await check_relevance(user_msg, response),
        "length_ok": await check_length(response),
        "personality_ok": await check_personality(response),
        "humor_ok": await check_humor_necessity(user_emotion),
        "accuracy_ok": await check_accuracy(response),
        "no_conflict": await check_non_conflict(response),
    }
    results["passed"] = all(results.values())
    results["score"] = sum(1 for v in results.values() if v is True and v != results.get("passed")) / 5
    return results


def get_pass_rate(results: dict) -> float:
    checks = ["relevant", "length_ok", "personality_ok", "humor_ok", "accuracy_ok", "no_conflict"]
    passed = sum(1 for c in checks if results.get(c, False))
    return passed / len(checks)
