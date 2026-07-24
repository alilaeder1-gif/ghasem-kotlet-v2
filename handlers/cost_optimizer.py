import time
import logging

logger = logging.getLogger(__name__)

_PROVIDER_COSTS = {
    "gemini": {"cost_per_1m": 0.075, "speed": "fast", "tier": 1},
    "groq_8b": {"cost_per_1m": 0.0, "speed": "fast", "tier": 1},
    "groq_70b": {"cost_per_1m": 0.0, "speed": "fast", "tier": 2},
    "openrouter_qwen32b": {"cost_per_1m": 0.35, "speed": "medium", "tier": 2},
    "openrouter_deepseek": {"cost_per_1m": 0.14, "speed": "medium", "tier": 2},
    "openrouter_hermes405b": {"cost_per_1m": 2.50, "speed": "medium", "tier": 3},
    "openrouter_gemma27b": {"cost_per_1m": 0.27, "speed": "medium", "tier": 2},
}

_INTENT_TIER_MAP = {
    "greeting": 1,
    "simple": 1,
    "general": 1,
    "emotional": 1,
    "coding": 2,
    "reasoning": 3,
    "sensitive": 2,
}

_RATE_LIMIT_WINDOW = 60
_MAX_CALLS_PER_WINDOW = {
    1: 30,
    2: 15,
    3: 5,
}

_call_log: list[tuple[int, str]] = []


def _count_calls_in_window(provider_key: str = None) -> int:
    now = time.time()
    cutoff = now - _RATE_LIMIT_WINDOW
    global _call_log
    _call_log = [(t, p) for t, p in _call_log if t > cutoff]
    if provider_key:
        return sum(1 for _, p in _call_log if p == provider_key)
    return len(_call_log)


def log_call(provider_key: str):
    _call_log.append((time.time(), provider_key))


def get_cost_tier(intent: str) -> int:
    return _INTENT_TIER_MAP.get(intent, 1)


def should_use_tier(tier: int) -> bool:
    calls = _count_calls_in_window()
    limit = _MAX_CALLS_PER_WINDOW.get(tier, 10)
    return calls < limit


def estimate_cost(intent: str, estimated_tokens: int = 500) -> float:
    tier = get_cost_tier(intent)
    best_price = float("inf")
    best_key = None
    for key, info in _PROVIDER_COSTS.items():
        if info["tier"] <= tier:
            price = (estimated_tokens / 1_000_000) * info["cost_per_1m"]
            if price < best_price:
                best_price = price
                best_key = key
    return best_price, best_key


def _check_rate_limits() -> dict:
    free_calls = _count_calls_in_window("groq_8b") + _count_calls_in_window("groq_70b")
    return {
        "free_calls_last_60s": free_calls,
        "total_calls_last_60s": _count_calls_in_window(),
        "groq_rate_limited": free_calls > 20,
    }
