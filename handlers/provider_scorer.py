"""Provider Scoring — score providers by latency/success/cost/quota for optimal routing.

Scores are stored in Redis (fast) and synced to DB (persistent).
Higher score = better provider for a given intent.
"""
import logging
import time

from database import db

logger = logging.getLogger(__name__)

# Intent → weight multipliers
_INTENT_WEIGHTS = {
    "coding": {"latency": 0.1, "success": 0.4, "quality": 0.4, "cost": 0.1},
    "general": {"latency": 0.3, "success": 0.3, "quality": 0.2, "cost": 0.2},
    "creative": {"latency": 0.1, "success": 0.3, "quality": 0.5, "cost": 0.1},
    "long_text": {"latency": 0.2, "success": 0.3, "quality": 0.3, "cost": 0.2},
    "quick": {"latency": 0.5, "success": 0.3, "quality": 0.1, "cost": 0.1},
}

# Maximum scores per dimension
_MAX_SCORE = 100


class ProviderScore:
    def __init__(self):
        self._scores: dict[str, dict] = {}  # provider -> stats

    async def record(self, provider: str, model: str, success: bool, latency: float, intent: str, cost: float = 0):
        if provider not in self._scores:
            self._scores[provider] = {
                "calls": 0, "success": 0, "failures": 0,
                "total_latency": 0, "total_cost": 0,
                "last_seen": 0, "models": set(),
            }
        s = self._scores[provider]
        s["calls"] += 1
        if success:
            s["success"] += 1
        else:
            s["failures"] += 1
        s["total_latency"] += latency
        s["total_cost"] += cost
        s["last_seen"] = time.time()
        s["models"].add(model)

        # Persist to DB
        try:
            await db.record_provider_result(provider, success, latency)
        except:
            pass

    def _rate(self, provider: str) -> dict:
        s = self._scores.get(provider, {})
        calls = s.get("calls", 1)
        success_rate = (s.get("success", 0) / calls) * 100 if calls else 0
        avg_latency = s.get("total_latency", 0) / calls if calls else 1000
        # Normalize latency: <500ms = 100, >5000ms = 0
        latency_score = max(0, min(100, 100 - (avg_latency - 500) / 45))
        cost_per_call = s.get("total_cost", 0) / calls if calls else 0
        cost_score = max(0, min(100, 100 - cost_per_call * 1000))
        return {
            "success_score": success_rate,
            "latency_score": latency_score,
            "cost_score": cost_score,
            "quality_score": (success_rate + latency_score) / 2,
            "avg_latency_ms": round(avg_latency, 0),
            "success_rate": round(success_rate, 1),
            "total_calls": calls,
        }

    def score(self, provider: str, intent: str = "general") -> float:
        """Calculate overall score for a provider given an intent."""
        rates = self._rate(provider)
        weights = _INTENT_WEIGHTS.get(intent, _INTENT_WEIGHTS["general"])

        score = (
            rates["success_score"] * weights["success"]
            + rates["latency_score"] * weights["latency"]
            + rates["quality_score"] * weights["quality"]
            + rates["cost_score"] * weights["cost"]
        )
        return score

    def best_provider(self, intent: str = "general", candidates: list[str] = None) -> str | None:
        """Return the best provider for this intent among candidates."""
        providers = candidates or list(self._scores.keys())
        if not providers:
            return None
        scored = [(p, self.score(p, intent)) for p in providers]
        scored.sort(key=lambda x: -x[1])
        return scored[0][0]

    def all_scores(self) -> dict[str, dict]:
        return {p: self._rate(p) for p in self._scores}


provider_scorer = ProviderScore()
