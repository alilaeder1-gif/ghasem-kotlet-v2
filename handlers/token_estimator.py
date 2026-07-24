# Observed prompt token limits per model (from prod)
# Includes OpenRouter free-tier caps (much lower than model native)
MODEL_LIMITS: dict[str, int] = {
    "gemini-2.0-flash": 30000,
    "llama-3.3-70b-versatile": 28000,
    "llama-3.1-8b-instant": 7000,
    "nousresearch/hermes-3-llama-3.1-405b": 4000,
    "nousresearch/hermes-2-pro-mistral-7b": 8000,
    "nousresearch/hermes-2-theta-llama-3-8b": 8000,
    "qwen/qwen-2.5-coder-32b-instruct": 30000,
    "deepseek/deepseek-chat": 10000,
    "google/gemma-2-27b-it": 8000,
}

_SAFETY = 2000  # reserve for user msg + history overhead


def estimate_tokens(text: str) -> int:
    return len(text) // 4 if text else 0


def get_limit(model: str) -> int:
    return MODEL_LIMITS.get(model, 8000)


def fits(model: str, text: str, overhead: int = 0) -> bool:
    return estimate_tokens(text) + _SAFETY + overhead <= get_limit(model)


def best_tier(model: str, tiers: dict, overhead: int = 0) -> str | None:
    for name in ("full", "lite", "micro"):
        t = tiers.get(name)
        if t and fits(model, t, overhead):
            return name
    return None
