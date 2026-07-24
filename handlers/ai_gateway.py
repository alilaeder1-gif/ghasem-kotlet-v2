import time
import logging
from datetime import datetime, timezone
from handlers.token_estimator import estimate_tokens, fits, best_tier

logger = logging.getLogger(__name__)

TOKEN_BUDGET = 12000
HISTORY_WINDOW = 6


class DailyUsage:
    def __init__(self):
        self._data: dict[str, dict] = {}

    def _today(self):
        return datetime.now(timezone.utc).date()

    def record(self, key: str, tokens: int):
        today = self._today()
        entry = self._data.get(key)
        if not entry or entry.get("date") != today:
            self._data[key] = {"tokens": 0, "calls": 0, "date": today}
        self._data[key]["tokens"] += tokens
        self._data[key]["calls"] += 1

    def get_usage(self, key: str) -> dict:
        today = self._today()
        entry = self._data.get(key)
        if entry and entry.get("date") == today:
            return {"tokens": entry["tokens"], "calls": entry["calls"]}
        return {"tokens": 0, "calls": 0}


class TokenBudget:
    @staticmethod
    def compress_history(history: list, max_tokens: int = TOKEN_BUDGET) -> list:
        if not history:
            return []
        total = 0
        kept = []
        for msg in reversed(history):
            t = estimate_tokens(msg.get("content", ""))
            if total + t > max_tokens:
                break
            kept.insert(0, msg)
            total += t
        return kept

    @staticmethod
    def select_history(prompt_tokens: int, history: list, tier: str) -> list:
        budget = TOKEN_BUDGET - prompt_tokens - 500
        if budget <= 0:
            return []
        if tier == "full":
            return TokenBudget.compress_history(history, budget)
        if tier == "lite":
            budget = min(budget, 2000)
            return TokenBudget.compress_history(history, budget)[-2:]
        return []


class HealthScore:
    _DECAY = 0.95

    def __init__(self):
        self._scores: dict[str, float] = {}

    def record(self, model: str, success: bool, latency: float = 0):
        old = self._scores.get(model, 50.0)
        if success:
            new = old * self._DECAY + 100 * (1 - self._DECAY)
        else:
            penalty = min(30, latency / 2) if latency > 0 else 15
            new = old * self._DECAY - penalty * (1 - self._DECAY)
        self._scores[model] = max(0, min(100, new))

    def get(self, model: str) -> float:
        return self._scores.get(model, 50.0)


daily_usage = DailyUsage()
health_score = HealthScore()


def make_tiers(system_prompt: str, lite_prompt: str = "", micro_prompt: str = "") -> dict:
    return {
        "full": system_prompt,
        "lite": lite_prompt if lite_prompt and lite_prompt != system_prompt else "",
        "micro": micro_prompt if micro_prompt and micro_prompt != (lite_prompt or system_prompt) else "",
    }


def smart_route(intent: str, tiers: dict, history_len: int) -> list:
    intent_tier_map = {
        "greeting": ("full", "lite"),
        "simple": ("full", "lite"),
        "coding": ("full", "lite", "micro"),
        "reasoning": ("full", "lite"),
        "emotional": ("full", "lite"),
        "sensitive": ("full", "lite"),
        "general": ("full", "lite", "micro"),
    }
    preferred_tiers = intent_tier_map.get(intent, ("full", "lite", "micro"))
    candidates = []
    history_overhead = min(history_len, HISTORY_WINDOW) * 300

    for provider, model, cost_tier, models_list, pool_name in _PROVIDER_ROSTER:
        score = health_score.get(model)
        if score < 10:
            continue
        for t in preferred_tiers:
            text = tiers.get(t)
            if not text:
                continue
            if fits(model, text, history_overhead):
                candidates.append({
                    "provider": provider,
                    "model": model,
                    "tier": t,
                    "cost": cost_tier,
                    "health": score,
                    "pool": pool_name,
                    "models": models_list,
                })
                break
    candidates.sort(key=lambda c: (c["cost"] != "free", -c["health"]))
    return candidates


_PROVIDER_ROSTER = [
    ("gemini", "gemini-2.0-flash", "free", None, "gemini"),
    ("groq", "llama-3.3-70b-versatile", "free", None, "groq"),
    ("groq", "llama-3.1-8b-instant", "free", None, "groq"),
    ("openrouter", "nousresearch/hermes-3-llama-3.1-405b", "low", None, "openrouter"),
    ("openrouter", "deepseek/deepseek-chat", "low", None, "openrouter"),
    ("openrouter", "qwen/qwen-2.5-coder-32b-instruct", "low", None, "openrouter"),
    ("openrouter", "google/gemma-2-27b-it", "low", None, "openrouter"),
    ("openrouter", "nousresearch/hermes-2-pro-mistral-7b", "low", None, "openrouter"),
    ("openrouter", "nousresearch/hermes-2-theta-llama-3-8b", "low", None, "openrouter"),
]
