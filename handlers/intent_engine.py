"""AI Intent Classification Engine.

This module ONLY classifies text into intents — it NEVER generates responses.
The response always comes from the database (offline_answers table).

Flow:
  1. Build known intents list from offline_answers
  2. Send a lightweight AI request asking to classify
  3. Return {"intent_name": "xxx", "confidence": 0.xx}
  4. Caller looks up the response from the DB
"""

import json
import logging
from database import db

logger = logging.getLogger(__name__)

_INTENT_CACHE: list[dict] = []
_INTENT_CACHE_TIME: float = 0
import time

# System prompt used for AI intent classification (very short & cheap)
_SYSTEM_PROMPT = """You are an intent classifier. Your ONLY job is to output JSON.

Rules:
- NEVER generate a response to the user.
- NEVER add explanations.
- ONLY output a single JSON object.

Output format:
{"intent_name": "name", "intent_id": 0, "confidence": 0.0}

If the message does not match any known intent, use intent_name="unknown"."""


async def _load_intents() -> list[dict]:
    global _INTENT_CACHE, _INTENT_CACHE_TIME
    now = time.time()
    if now - _INTENT_CACHE_TIME > 30:
        rows = await db.get_all_offline_answers()
        _INTENT_CACHE = rows or []
        _INTENT_CACHE_TIME = now
    return _INTENT_CACHE


def _build_intent_list(intents: list[dict]) -> str:
    """Build a compact intent mapping string for the AI prompt."""
    lines = []
    for entry in intents:
        iid = entry.get("intent_id", 0)
        name = entry.get("intent", "?")
        triggers = entry.get("triggers", "")
        lines.append(f"  {iid:>4} = {name:20s} ({triggers})")
    return "\n".join(lines)


async def classify(text: str, use_ai: bool = True) -> dict:
    """Classify text into an intent.

    Returns dict with intent_name, intent_id, confidence.
    If classification fails, returns {"intent_name": "unknown", "intent_id": 0, "confidence": 0}.
    """
    intents = await _load_intents()
    intent_map = _build_intent_list(intents)

    # First: try keyword match (fast path, no AI)
    clean = text.lower().strip()
    for entry in intents:
        triggers = [t.strip().lower() for t in entry.get("triggers", "").split(",")]
        for t in triggers:
            if t and t in clean:
                return {
                    "intent_name": entry.get("intent", "unknown"),
                    "intent_id": entry.get("intent_id", 0),
                    "confidence": 1.0,
                }

    if not use_ai:
        return {"intent_name": "unknown", "intent_id": 0, "confidence": 0.0}

    # Build the user prompt for AI
    if intents:
        user_prompt = (
            f"Known intents:\n{intent_map}\n\n"
            f"User message: \"{text[:300]}\"\n\n"
            f"Respond with JSON only: {{\"intent_name\": \"...\", \"intent_id\": 0, \"confidence\": 0.0}}"
        )
    else:
        user_prompt = (
            f"User message: \"{text[:300]}\"\n\n"
            f"If message looks like a greeting,{{\"intent_name\":\"greeting\",\"intent_id\":0,\"confidence\":0.0}}\n"
            f"Otherwise: {{\"intent_name\":\"unknown\",\"intent_id\":0,\"confidence\":0.0}}"
        )

    # Use a cheap/fast AI call for classification
    try:
        response = await _ai_classify(_SYSTEM_PROMPT, user_prompt)
        result = json.loads(response)
        return {
            "intent_name": result.get("intent_name", "unknown"),
            "intent_id": result.get("intent_id", 0),
            "confidence": result.get("confidence", 0.0),
        }
    except Exception as e:
        logger.warning(f"AI intent classification failed: {e}")
        return {"intent_name": "unknown", "intent_id": 0, "confidence": 0.0}


async def _ai_classify(system_prompt: str, user_prompt: str) -> str:
    """Make a cheap AI call for intent classification only.

    Tries providers in order: gemini → groq → fallback.
    Returns raw response text.
    """
    from bot import ask_with_routing
    from handlers.router import route
    from handlers.personality_core import build_lite_prompt

    route_decision = route(user_prompt, is_group=False)
    # Override: always use cheapest model for classification
    route_decision.preferred_provider = "groq"
    route_decision.preferred_model = "llama-3.1-8b-instant"
    route_decision.max_tokens = 64
    route_decision.temperature = 0.1
    route_decision.humor_ok = False

    result = await ask_with_routing(
        user_msg=user_prompt,
        system_prompt=system_prompt,
        history=[],
        user_memory="",
        qa_context="",
        route=route_decision,
        fallback_prompt=build_lite_prompt(),
    )
    return result or ""


def clear_cache():
    global _INTENT_CACHE, _INTENT_CACHE_TIME
    _INTENT_CACHE.clear()
    _INTENT_CACHE_TIME = 0
