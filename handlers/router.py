import re
from dataclasses import dataclass

@dataclass
class RouteDecision:
    intent: str
    preferred_provider: str
    preferred_model: str
    humor_ok: bool
    max_tokens: int
    temperature: float
    description: str

_INTENT_PATTERNS = {
    "coding": re.compile(
        r"(کد|برنامه|پایتون|جاوا|php|css|html|جاوااسکریپت|javascript|typescript|"
        r"script|function|api|endpoint|bug|error|الگوریتم|algorithm|دیتابیس|database|"
        r"frontend|backend|fullstack|git|commit|push|deploy|debug|سینتکس|syntax)",
        re.IGNORECASE,
    ),
    "reasoning": re.compile(
        r"(چرا|دلیل|تحلیل|بررسی|مقایسه|تفاوت|فرق|اثبات|توجیه|منطق|"
        r"فلسفه|استراتژی|پیش‌بینی|سناریو|conclusion|بنظرت|نظرت چیه)",
        re.IGNORECASE,
    ),
    "emotional": re.compile(
        r"(غمگین|ناراحت|افسرد|دلتنگ|تنها|استرس|اضطراب|عصبانی|خسته|"
        r"دلم گرفته|حالم بده|کمک کن|تنهام گذاشت|شکستم|داغون)",
        re.IGNORECASE,
    ),
    "sensitive": re.compile(
        r"(خودکشی|مرگ|بیماری لاعلاج|طلاق|اعتیاد|سیاست|دین|مذهب|"
        r"سیگار|مشروب|مواد مخدر|خیانت|تجاوز|جنایت)",
        re.IGNORECASE,
    ),
    "greeting": re.compile(
        r"^(س+ل+ا*م*|درود|علیک|خوبی|چطوری|خوش اومدی|چخبر|چه خبر)",
        re.IGNORECASE,
    ),
    "simple": re.compile(
        r"^.{0,30}$",
    ),
}

_IRAN_KEYWORDS = re.compile(
    r"(ایران|تهران|اصفهان|شیراز|تبریز|مشهد|فارس|کرد|لر|ترک|گیل|مازند|"
    r"خوزستان|فرهنگ|تاریخ|جشن|نوروز|سیزده|شب یلدا|محرم|رمضان|عید|"
    r"قاجار|پهلوی|هخامنش|ساسانی|صفوی|شاه)", re.IGNORECASE,
)

_CODE_KEYWORDS = re.compile(
    r"(def |class |import |const |var |function|docker|npm|pip|"
    r"git |html|<div|<script|console\.|return |=>|async|await)",
    re.IGNORECASE,
)


def classify_intent(user_message: str) -> str:
    if _CODE_KEYWORDS.search(user_message):
        return "coding"
    for intent, pattern in _INTENT_PATTERNS.items():
        if pattern.search(user_message):
            return intent
    return "general"


def detect_topic(user_message: str) -> list:
    topics = []
    if _IRAN_KEYWORDS.search(user_message):
        topics.append("iran")
    if _CODE_KEYWORDS.search(user_message):
        topics.append("coding")
    return topics


_PROVIDER_PRIORITY = {
    "gemini": {
        "models": ["gemini-2.0-flash"],
        "cost": "low",
        "speed": "fast",
        "strengths": ["general", "greeting", "simple", "emotional"],
    },
    "groq": {
        "models": ["llama-3.3-70b-versatile", "llama-3.1-8b-instant"],
        "cost": "free",
        "speed": "fast",
        "strengths": ["coding", "reasoning", "general"],
    },
    "openrouter": {
        "models": [
            "nousresearch/hermes-3-llama-3.1-405b",
            "qwen/qwen-2.5-coder-32b-instruct",
            "deepseek/deepseek-chat",
            "google/gemma-2-27b-it",
        ],
        "cost": "variable",
        "speed": "medium",
        "strengths": ["reasoning", "coding", "sensitive", "emotional"],
    },
}

_INTENT_ROUTES = {
    "coding": RouteDecision(
        intent="coding",
        preferred_provider="groq",
        preferred_model="llama-3.3-70b-versatile",
        humor_ok=False,
        max_tokens=512,
        temperature=0.3,
        description="فنی و دقیق، شوخی محدود",
    ),
    "reasoning": RouteDecision(
        intent="reasoning",
        preferred_provider="openrouter",
        preferred_model="nousresearch/hermes-3-llama-3.1-405b",
        humor_ok=False,
        max_tokens=512,
        temperature=0.5,
        description="تحلیلی و عمیق",
    ),
    "emotional": RouteDecision(
        intent="emotional",
        preferred_provider="gemini",
        preferred_model="gemini-2.0-flash",
        humor_ok=False,
        max_tokens=256,
        temperature=0.7,
        description="همدلانه، آرام، بدون شوخی",
    ),
    "sensitive": RouteDecision(
        intent="sensitive",
        preferred_provider="openrouter",
        preferred_model="google/gemma-2-27b-it",
        humor_ok=False,
        max_tokens=256,
        temperature=0.4,
        description="موضوع حساس، محتاط و ایمن",
    ),
    "greeting": RouteDecision(
        intent="greeting",
        preferred_provider="gemini",
        preferred_model="gemini-2.0-flash",
        humor_ok=True,
        max_tokens=128,
        temperature=0.8,
        description="سلام و احوالپرسی ساده",
    ),
    "simple": RouteDecision(
        intent="simple",
        preferred_provider="gemini",
        preferred_model="gemini-2.0-flash",
        humor_ok=True,
        max_tokens=128,
        temperature=0.8,
        description="سوال کوتاه و ساده",
    ),
    "general": RouteDecision(
        intent="general",
        preferred_provider="gemini",
        preferred_model="gemini-2.0-flash",
        humor_ok=True,
        max_tokens=256,
        temperature=1.0,
        description="مکالمه عمومی",
    ),
}


def route(user_message: str, is_group: bool = False) -> RouteDecision:
    intent = classify_intent(user_message)
    route = _INTENT_ROUTES.get(intent, _INTENT_ROUTES["general"])
    if is_group:
        route.max_tokens = min(route.max_tokens, 128)
    return route


def get_failover_chain(route: RouteDecision) -> list[tuple[str, str]]:
    provider_order = ["gemini", "groq", "openrouter"]
    preferred = route.preferred_provider
    ordered = [preferred] + [p for p in provider_order if p != preferred]
    chain = []
    for provider in ordered:
        info = _PROVIDER_PRIORITY.get(provider)
        if info:
            for model in info["models"]:
                chain.append((provider, model))
    return chain
