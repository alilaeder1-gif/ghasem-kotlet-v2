"""Smart AI Router — routes requests by intent to the best provider.

Intent detection + provider routing table + canary support.

Route table:
  coding    → claude → deepseek → qwen
  general   → gemini → groq → openrouter
  creative  → claude → gemini → groq
  long_text → qwen-72b → claude → deepseek
  quick     → groq-8b → gemini-flash
"""
import logging
import re

from handlers.provider_scorer import provider_scorer

logger = logging.getLogger(__name__)

# Intent detection patterns
_INTENT_PATTERNS = {
    "coding": [
        r"(def |function |class |import |from |const |let |var |#include|print\(|console\.|return |async |await )",
        r"(programming|code|debug|compile|syntax|script|api|endpoint|database|sql|query|json|html|css|js|python|javascript|typescript|go|rust|c\+\+|java)",
        r"(الگوریتم|برنامه|کد|خطا|باگ|دیتابیس|سرور|api|sql|python)",
    ],
    "creative": [
        r"(write|create|design|draw|poem|story|song|idea|suggest|imagine|fantasy)",
        r"(نوشتن|داستان|شعر|ایده|خلاقیت|نقاشی|دیزاین|داستانی)",
    ],
    "long_text": [
        r"(.{500,})",
    ],
    "quick": [
        r"^(hi|hello|سلام|چطوری|خوبی|مرسی|داداش|😂|😎)$",
        r"^\S{1,20}$",
    ],
}

# Route table: intent → ordered list of provider:model
_ROUTES = {
    "coding": [
        ("gemini", "gemini-2.0-flash"),
        ("groq", "llama-3.3-70b-versatile"),
        ("openrouter", "deepseek/deepseek-chat"),
    ],
    "general": [
        ("gemini", "gemini-2.0-flash"),
        ("groq", "llama-3.1-8b-instant"),
        ("openrouter", "deepseek/deepseek-chat"),
    ],
    "creative": [
        ("gemini", "gemini-2.0-flash"),
        ("groq", "llama-3.3-70b-versatile"),
        ("openrouter", "deepseek/deepseek-chat"),
    ],
    "long_text": [
        ("gemini", "gemini-2.0-flash"),
        ("openrouter", "deepseek/deepseek-chat"),
    ],
    "quick": [
        ("groq", "llama-3.1-8b-instant"),
        ("gemini", "gemini-2.0-flash"),
    ],
}

_DEFAULT_INTENT = "general"


def detect_intent(text: str) -> str:
    """Detect user intent from message text."""
    if len(text) > 400:
        return "long_text"
    for intent, patterns in _INTENT_PATTERNS.items():
        for p in patterns:
            if re.search(p, text, re.IGNORECASE):
                return intent
    return _DEFAULT_INTENT


class AICanary:
    """Gradual rollout: 5% → 20% → 50% → 100% of users get new routes."""
    def __init__(self):
        self._enabled = True
        self._rollout_pct = 100  # start at 100% for now

    def in_canary(self, user_id: int) -> bool:
        """Check if user is in canary group."""
        if not self._enabled:
            return True
        return (user_id % 100) < self._rollout_pct

    def set_rollout(self, pct: int):
        self._rollout_pct = max(5, min(100, pct))


canary = AICanary()


def get_route(intent: str, user_id: int = 0) -> list[tuple[str, str]]:
    """Get ordered provider:model list for this intent and user."""
    route = list(_ROUTES.get(intent, _ROUTES[_DEFAULT_INTENT]))

    # Try to reorder by score if we have data
    if provider_scorer._scores:
        scored = []
        for provider, model in route:
            s = provider_scorer.score(provider, intent)
            scored.append((s, provider, model))
        scored.sort(key=lambda x: -x[0])
        route = [(p, m) for _, p, m in scored]

    return route
