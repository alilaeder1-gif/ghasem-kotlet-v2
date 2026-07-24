import os
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

FEW_SHOT = (
    _read_example("coding.md") + "\n\n" +
    _read_example("jokes.md") + "\n\n" +
    _read_example("debate.md") + "\n\n" +
    _read_example("group.md") + "\n\n" +
    _read_example("support.md") + "\n\n" +
    _read_example("casual.md")
)

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


def build_persona_prompt(settings: dict) -> str:
    parts = [
        PERSONA_HEADER,
        EMOTIONS,
        HUMOR,
        SLANG,
        IRAN,
        HISTORY,
        MEMORY,
        REASONING,
        GROUP_MODE,
        GROUP_INTELLIGENCE,
        ANTI_CRINGE,
        ANTI_AI,
        ANTI_INJECTION,
        REFLECTION,
        CONSISTENCY,
        CONFIDENCE,
        SHORT_TERM_MEMORY,
        STYLE_RANDOMIZATION,
        STATE_MACHINE,
        PERSONA_LOCK,
        DEVELOPER,
        GOAL_ENGINE,
        INTENT_ENGINE,
        PERSONALITY_BLEND,
        COOLDOWN_SYSTEM,
        LEARNING_ENGINE,
        WORLD_MODEL,
        PERSONA_LORE,
        DYNAMIC_CATCHPHRASES,
        ANTI_LOOP,
        HUMAN_IMPERFECTION,
        BEHAVIOR,
        BEHAVIOR_TREE_SECTION,
        MEMORY_BANK_REFERENCE,
    ]

    friend = int(settings.get("friendliness", 9))
    humor = int(settings.get("humor_level", 9))
    sarcasm = int(settings.get("sarcasm_level", 6))
    confidence = int(settings.get("confidence", 9))
    empathy = int(settings.get("empathy", 8))
    tehran = int(settings.get("tehran_accent", 9))
    street = int(settings.get("street_language", 8))
    energy = int(settings.get("energy", 9))
    patience = int(settings.get("patience", 6))

    parts.append(
        "\n## لغزنده‌ها\n"
        f"دوستانه: {friend}/10 | طنز: {humor}/10 | كنايه: {sarcasm}/10 | "
        f"اعتمادبه‌نفس: {confidence}/10 | همدلي: {empathy}/10 | "
        f"لهجه تهراني: {tehran}/10 | كوچه‌بازاري: {street}/10 | "
        f"انرژي: {energy}/10 | صبر: {patience}/10"
    )

    tone = settings.get("ai_tone", "tehrani")
    tone_map = {
        "tehrani": "لحن: تهروني خيابوني با انرژي. كلمات: داداش، بابا، دمت گرم، حله",
        "turkish": "لحن: تركي آذربايجاني. كلمات: قارداش، بالا، گوزل",
        "kurdish": "لحن: كردي. كلمات: برات، زور، باشه",
        "gilaki": "لحن: گيلكي. كلمات: زاك، كولي، ميرزا",
        "normal": "لحن: فارسي روان و معمولي.",
    }
    parts.append(tone_map.get(tone, tone_map["tehrani"]))

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
    parts.append(beh_map.get(behavior, beh_map["default"]))

    personality = settings.get("ai_personality", 3)
    pers_map = {
        1: "شخصيت: رباتي خشك. فقط سوال و جواب.",
        2: "شخصيت: معمولي نسبتاً مختصر.",
        3: "شخصيت: خودموني معمولي.",
        4: "شخصيت: باحال پرانرژي.",
        5: "شخصيت: پررو و بي‌پروا.",
    }
    parts.append(pers_map.get(personality, pers_map[3]))

    parts.append(
        "## قانون نهايي\n"
        "هميشه كوتاه جواب بده. حداكثر ۱-۲ جمله مگر اينكه كاربر توضيح بخواد.\n"
        "از اموجي كم و هوشمندانه استفاده كن. آخر بعضي جملات يه اموجي مناسب.\n\n"
        "## نمونه مكالمه\n"
        + FEW_SHOT
    )

    return "\n\n".join(parts)
