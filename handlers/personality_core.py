import os
import random
from handlers import memory_bank

_PERSONA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "persona")


def _read(filename: str) -> str:
    try:
        with open(os.path.join(_PERSONA_DIR, filename), "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


def _read_example(filename: str) -> str:
    try:
        with open(os.path.join(_PERSONA_DIR, "examples", filename), "r", encoding="utf-8") as f:
            return f.read().strip()
    except Exception:
        return ""


# ---- Load all modules ----
PERSONA_HEADER = _read("identity.md")
EMOTIONS = _read("emotions.md")
HUMOR = _read("humor.md")
SLANG = _read("slang.md")
IRAN = _read("iran.md")
HISTORY = _read("history.md")
MEMORY = _read("memory.md")
REASONING = _read("reasoning.md")
GROUP_MODE = _read("group_mode.md")
ANTI_CRINGE = _read("anti_cringe.md")
ANTI_AI = _read("anti_ai.md")
REFLECTION = _read("reflection.md")
STATE_MACHINE = _read("state_machine.md")
BEHAVIOR = _read("behavior.md")
PERSONA_LOCK = _read("persona_lock.md")
ANTI_INJECTION = _read("anti_injection.md")
CONSISTENCY = _read("consistency.md")
GROUP_INTELLIGENCE = _read("group_intelligence.md")
SHORT_TERM_MEMORY = _read("short_term_memory.md")
CONFIDENCE = _read("confidence.md")
STYLE_RANDOMIZATION = _read("style_randomization.md")
DEVELOPER = _read("developer.md")
GOAL_ENGINE = _read("goal_engine.md")
INTENT_ENGINE = _read("intent_engine.md")
PERSONALITY_BLEND = _read("personality_blend.md")
COOLDOWN_SYSTEM = _read("cooldown_system.md")
LEARNING_ENGINE = _read("learning_engine.md")
WORLD_MODEL = _read("world_model.md")
PERSONA_LORE = _read("persona_lore.md")
DYNAMIC_CATCHPHRASES = _read("dynamic_catchphrases.md")
ANTI_LOOP = _read("anti_loop.md")
HUMAN_IMPERFECTION = _read("human_imperfection.md")
HALLUCINATION_GUARD = _read("hallucination_guard.md")
DEVELOPER_DASHBOARD = _read("developer_dashboard.md")
ANALYTICS = _read("analytics.md")
USER_RELATIONSHIPS = _read("user_relationships.md")
CHARACTER_EVOLUTION = _read("character_evolution.md")
GROUP_MODES = _read("group_modes.md")
QUALITY_GATE = _read("quality_gate.md")
PERSONA_SIGNATURE = _read("persona_signature.md")
RESPONSE_JUDGE = _read("response_judge.md")
COST_OPTIMIZER = _read("cost_optimizer.md")
AB_TEST = _read("ab_test.md")
CONVERSATION_SUMMARY = _read("conversation_summary.md")
EMERGENCY_MODE = _read("emergency_mode.md")

ALL_EXAMPLES = {
    "coding": _read_example("coding.md"),
    "jokes": _read_example("jokes.md"),
    "debate": _read_example("debate.md"),
    "group": _read_example("group.md"),
    "support": _read_example("support.md"),
    "casual": _read_example("casual.md"),
}

BEHAVIOR_TREE_SECTION = memory_bank.build_behavior_instruction()

MEMORY_BANK_REFERENCE = (
    "## حافظه فرهنگي\n"
    f"- ضرب‌المثل‌ها: بيش از {len(memory_bank.PROVERBS)} ضرب‌المثل فارسي در حافظه\n"
    f"- اصطلاحات تهراني: بيش از {len(memory_bank.TEHRANI_EXPRESSIONS)} اصطلاح تهروني\n"
    f"- اصطلاحات دهه‌ها: {len(memory_bank.EXPRESSIONS_70S)} تا دهه ۷۰، {len(memory_bank.EXPRESSIONS_80S)} تا دهه ۸۰، {len(memory_bank.EXPRESSIONS_90S)} تا دهه ۹۰، {len(memory_bank.EXPRESSIONS_1400S)} تا دهه ۱۴۰۰\n"
    f"- ميم‌هاي ايراني: {len(memory_bank.IRANIAN_MEMES)} ميم معروف\n"
    f"- شخصيت‌هاي معروف: {len(memory_bank.PERSIAN_PERSONALITIES)} شخصيت ايراني\n"
    f"- دانش تاريخ و فرهنگ ايران: هخامنشيان، ساسانيان، اسلام، صفويه، قاجار، پهلوي، انقلاب، دفاع مقدس\n"
    f"- استان‌ها: اطلاعات {len(memory_bank.KNOWLEDGE_BASE.get('استان‌ها', {}))} استان ايران\n"
    f"- غذاها: {len(memory_bank.KNOWLEDGE_BASE.get('غذاها', {}))} غذاي سنتي ايراني\n"
    f"- سينما: {len(memory_bank.KNOWLEDGE_BASE.get('سينما', {}))} كارگردان مطرح ايراني\n"
    f"- ترندهاي اخير: {len(memory_bank.RECENT_TRENDS)} ترند روز ايران"
)

# ---- Module categorization ----

_CORE_MODULES = [
    "PERSONA_HEADER", "EMOTIONS", "BEHAVIOR", "PERSONA_LOCK",
    "CONFIDENCE", "HUMAN_IMPERFECTION", "STYLE_RANDOMIZATION",
    "SLANG", "ANTI_AI", "ANTI_INJECTION", "ANTI_LOOP",
    "CONSISTENCY", "SHORT_TERM_MEMORY", "PERSONALITY_BLEND",
    "COOLDOWN_SYSTEM", "HALLUCINATION_GUARD", "QUALITY_GATE",
    "PERSONA_SIGNATURE", "ANTI_CRINGE", "STATE_MACHINE",
    "REFLECTION", "GOAL_ENGINE", "INTENT_ENGINE",
    "DYNAMIC_CATCHPHRASES", "LEARNING_ENGINE", "WORLD_MODEL",
    "MEMORY", "REASONING", "HUMOR",
    "ANALYTICS", "USER_RELATIONSHIPS", "CHARACTER_EVOLUTION",
    "RESPONSE_JUDGE", "COST_OPTIMIZER", "AB_TEST",
    "CONVERSATION_SUMMARY", "EMERGENCY_MODE",
]

_GROUP_MODULES = [
    "GROUP_MODE", "GROUP_INTELLIGENCE", "GROUP_MODES",
]

_TOPIC_MODULES = {
    "iran": "IRAN",
    "history": "HISTORY",
    "developer": "DEVELOPER",
}


def _pick_examples(context: dict = None) -> str:
    count = min(2, len(ALL_EXAMPLES))
    keys = list(ALL_EXAMPLES.keys())
    if context and context.get("intent") == "coding":
        keys = ["coding"] + [k for k in keys if k != "coding"]
    elif context and context.get("intent") == "support":
        keys = ["support"] + [k for k in keys if k != "support"]
    selected = keys[:count]
    return "\n\n".join(ALL_EXAMPLES[k] for k in selected if ALL_EXAMPLES[k])


def _build_sliders(settings: dict) -> str:
    parts = []
    for key in ["friendliness", "humor_level", "sarcasm_level", "confidence",
                 "empathy", "tehran_accent", "street_language", "energy", "patience"]:
        parts.append(f"{key}: {int(settings.get(key, 9))}/10")
    return "\n".join(parts)


def _build_behavior_settings(settings: dict) -> str:
    tone = settings.get("ai_tone", "tehrani")
    tone_map = {
        "tehrani": "لحن: تهروني خيابوني با انرژي. كلمات: داداش، بابا، دمت گرم، حله",
        "turkish": "لحن: تركي آذربايجاني. كلمات: قارداش، بالا، گوزل",
        "kurdish": "لحن: كردي. كلمات: برات، زور، باشه",
        "gilaki": "لحن: گيلكي. كلمات: زاك، كولي، ميرزا",
        "normal": "لحن: فارسي روان و معمولي.",
    }
    behavior = settings.get("ai_behavior", "default")
    beh_map = {
        "default": "رفتار: خودموني و باحال.",
        "friendly": "رفتار: بسيار گرم و صميمي.",
        "formal": "رفتار: رسمي و مؤدب.",
        "funny": "رفتار: شوخ و بامزه.",
        "cool": "رفتار: جوون امروزي ترند.",
        "polite": "رفتار: مؤدب.",
        "rude": "رفتار: گستاخ و تند.",
    }
    personality = settings.get("ai_personality", 3)
    pers_map = {
        1: "شخصيت: رباتي خشك. فقط سوال و جواب.",
        2: "شخصيت: معمولي نسبتاً مختصر.",
        3: "شخصيت: خودموني معمولي.",
        4: "شخصيت: باحال پرانرژي.",
        5: "شخصيت: پررو و بي‌پروا.",
    }
    return (
        f"{tone_map.get(tone, tone_map['tehrani'])}\n"
        f"{beh_map.get(behavior, beh_map['default'])}\n"
        f"{pers_map.get(personality, pers_map[3])}"
    )


def _resolve(name: str):
    return globals().get(name, "")


_LITE_MODULES = [
    "PERSONA_HEADER", "EMOTIONS", "BEHAVIOR", "SLANG",
    "CONFIDENCE", "HUMAN_IMPERFECTION", "ANTI_CRINGE",
    "PERSONALITY_BLEND", "QUALITY_GATE", "PERSONA_SIGNATURE",
]

_MICRO_MODULES = [
    "PERSONA_HEADER", "BEHAVIOR", "CONFIDENCE",
    "ANTI_CRINGE", "PERSONALITY_BLEND",
]


def build_lite_prompt() -> str:
    parts = [_resolve(m) for m in _LITE_MODULES if _resolve(m)]
    parts.append(
        "## قانون نهايي\n"
        "هميشه كوتاه جواب بده. حداكثر ۱-۲ جمله. از اموجي كم و هوشمندانه استفاده كن."
    )
    return "\n\n".join(parts)


def build_micro_prompt() -> str:
    parts = [_resolve(m) for m in _MICRO_MODULES if _resolve(m)]
    parts.append(
        "## قانون نهايي\n"
        "هميشه كوتاه جواب بده. حداكثر ۱-۲ جمله."
    )
    return "\n\n".join(parts)


def build_core_prompt() -> str:
    parts = [_resolve(m) for m in _CORE_MODULES if _resolve(m)]
    return "\n\n".join(parts)


def build_contextual_prompt(settings: dict, context: dict = None) -> str:
    parts = []
    context = context or {}
    is_group = context.get("is_group", False)
    topic = context.get("topic", "").lower()
    intent = context.get("intent", "")

    if is_group:
        for m in _GROUP_MODULES:
            if _resolve(m):
                parts.append(_resolve(m))

    for keyword, module_name in _TOPIC_MODULES.items():
        if keyword in topic:
            if _resolve(module_name):
                parts.append(_resolve(module_name))

    parts.append(_build_sliders(settings))
    parts.append(_build_behavior_settings(settings))

    parts.append(
        "## قانون نهايي\n"
        "هميشه كوتاه جواب بده. حداكثر ۱-۲ جمله مگر اينكه كاربر توضيح بخواد.\n"
        "از اموجي كم و هوشمندانه استفاده كن. آخر بعضي جملات يه اموجي مناسب."
    )

    examples = _pick_examples(context)
    if examples:
        parts.append("## نمونه مكالمه\n" + examples)

    return "\n\n".join(parts)


def build_persona_prompt(settings: dict, context: dict = None) -> str:
    context = context or {}
    parts = [build_core_prompt()]
    parts.append(build_contextual_prompt(settings, context))
    if context.get("include_developer_dashboard"):
        if DEVELOPER_DASHBOARD:
            parts.append(DEVELOPER_DASHBOARD)
    parts.append(BEHAVIOR_TREE_SECTION)
    parts.append(MEMORY_BANK_REFERENCE)
    return "\n\n".join(parts)
