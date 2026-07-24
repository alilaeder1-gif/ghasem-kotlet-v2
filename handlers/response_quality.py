import re

_MIN_LENGTH = 3
_MAX_LENGTH = 70
_TEHRANI_MARKERS = re.compile(
    r"(داداش|بابا|والا|راستش|حله|دمت|کُتلت|کتلت|رفیق|اختیار|قربان|"
    r"دقیقاً|خودتی|به به|وای|آره|نه|بیا|برو|ببین)",
    re.UNICODE,
)
_FIGHT_TRIGGERS = re.compile(
    r"(احمق|کثافت|گوه|فحش|کونی|جاکش|ننه|مادر)",
    re.UNICODE,
)
_EMPTY_RESPONSES = re.compile(
    r"^(پاسخی دریافت نشد|خطا|⚠|⏳|)$"
)


def check_length(response: str) -> bool:
    return _MIN_LENGTH <= len(response) <= _MAX_LENGTH


def check_personality(response: str) -> bool:
    return bool(_TEHRANI_MARKERS.search(response))


def check_relevance(user_msg: str, response: str) -> bool:
    if _EMPTY_RESPONSES.match(response):
        return False
    words = re.findall(r'[\wآ-ی]+', user_msg.lower())
    response_words = set(re.findall(r'[\wآ-ی]+', response.lower()))
    if not words:
        return True
    overlap = sum(1 for w in words if w in response_words)
    return overlap > 0


def check_humor_appropriateness(response: str, user_emotion: str) -> bool:
    bad_moods = {"annoyed", "sad", "angry", "negative"}
    if user_emotion in bad_moods:
        laugh_markers = re.search(r"(😂|🤣|😁|خنده|بامزه|جوک|شوخی)", response)
        if laugh_markers:
            return False
    return True


def check_no_conflict(response: str) -> bool:
    return not bool(_FIGHT_TRIGGERS.search(response))


def score_quality(response: str, user_msg: str = "", user_emotion: str = "") -> dict:
    results = {
        "length_ok": check_length(response),
        "personality_ok": check_personality(response),
        "relevant": check_relevance(user_msg, response) if user_msg else True,
        "humor_ok": check_humor_appropriateness(response, user_emotion),
        "no_conflict": check_no_conflict(response),
        "not_empty": not _EMPTY_RESPONSES.match(response),
    }
    checks = ["length_ok", "personality_ok", "relevant", "humor_ok", "no_conflict", "not_empty"]
    passed = sum(1 for c in checks if results.get(c, False))
    results["score"] = passed / len(checks)
    results["passed"] = results["score"] >= 0.67
    return results


def needs_failover(response: str, user_msg: str = "", user_emotion: str = "") -> bool:
    quality = score_quality(response, user_msg, user_emotion)
    return not quality["passed"]
