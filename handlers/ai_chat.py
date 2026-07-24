import logging
import os
import tempfile
import asyncio
import json
import re
from cache import cache

from handlers.key_pool import get_pool, classify_error, gemini_pool, groq_pool, openrouter_pool
from handlers.token_estimator import best_tier

logger = logging.getLogger(__name__)

_EMOJI_ANGRY = re.compile(r'[😡🤬👿💢]', re.UNICODE)
_EMOJI_SAD = re.compile(r'[😢😭😔😞🥺💔]', re.UNICODE)
_EMOJI_HAPPY = re.compile(r'[😊😂🤣😁😍🥰😎🎉]', re.UNICODE)
_EMOJI_JOKING = re.compile(r'[😜🤪😏😉]', re.UNICODE)
_WORD_ANGRY = re.compile(r'(عصبان|عصب|خشم|دیگه بس|بی‌ادب|کصشر|گوه|فحش)', re.UNICODE)
_WORD_SAD = re.compile(r'(غمگین|افسرد|دلم گرفته|بدبخت|بیچاره|دلشکست)', re.UNICODE)
_WORD_JOKING = re.compile(r'(شوخی|می‌خند|بامزه|خنده|جوک|طنز)', re.UNICODE)
_WORD_SERIOUS = re.compile(r'(علمی|دقیق|مستند|منبع|تحقیق|پایان‌نامه|مقاله|پروژه)', re.UNICODE)
_WORD_SARCASTIC = re.compile(r'(آفرین بهت|به به|دستت درد نکنه|چه باحال|واقعاً|عه عه)', re.UNICODE)
_WORD_SCARED = re.compile(r'(ترس|می‌ترس|وحشت|استرس|اضطراب|نگران)', re.UNICODE)
_WORD_GREETING = re.compile(r'(سلام|درود|علیک|خوبی|چطوری|خوش اومدی)', re.UNICODE)


def detect_emotion(text: str) -> str:
    if _EMOJI_ANGRY.search(text) or _WORD_ANGRY.search(text):
        return "annoyed"
    if _EMOJI_SAD.search(text) or _WORD_SAD.search(text) or _WORD_SCARED.search(text):
        return "serious"
    if _EMOJI_HAPPY.search(text) or _EMOJI_JOKING.search(text) or _WORD_JOKING.search(text) or _WORD_SARCASTIC.search(text):
        return "comedy"
    if _WORD_SERIOUS.search(text):
        return "serious"
    if _WORD_GREETING.search(text):
        return "friendly"
    return "normal"


def _get_key(provider: str) -> str | None:
    pool = get_pool(provider)
    return pool.get_key()

DEFAULT_PROMPT = "شخصیت کتلت (قاسم کتلت)، ۲۵ ساله، رفیق تهرونی. فارسی محاوره‌ای. کنایه و شوخی رو بفهم. کوتاه جواب بده. همیشه یه ایموجی آخرش."
"""
راهنمای کامل شخصیت کتلت در PERSONALITY.md شامل ۱۴ بخش:
هویت، قوانین رفتاری، لحن بددهن، اصطلاحات تهرانی، ترکی آذربایجانی، کردی و گیلکی، شوخی، مدیریت احساسات،
پاسخ به سؤالات، تاریخ و فرهنگ ایران، شناخت استان‌ها، دیالوگ نمونه،
قوانین ممنوعه، تنظیمات حافظه، کیفیت پاسخ، تغییر لحن بر اساس رفتار کاربر
"""

SEARCH_INSTRUCTION = (
    "\n\n[سیستم: اگه شوخی، کنایه، یا سوال خاصی بود اول SEARCH: <عبارت> بزن."
    "بعد از جستجو جواب نهایی رو بده. وگرنه عادی جواب بده.]"
)

SEARCH_PROMPT_TEMPLATE = (
    "نتایج جستجوی اینترنتی برای «{query}»:\n{results}\n\n"
    "حالا با استفاده از این اطلاعات به سوال کاربر جواب بده."
)

_google_client = None
_groq_client = None


def _get_google():
    global _google_client
    key = _get_key("gemini")
    if not key:
        return None
    try:
        from google import genai
        client = genai.Client(api_key=key)
        _google_client = (client, key)
        return _google_client
    except Exception as e:
        logger.error(f"Gemini init error: {e}")
        return None


def _get_groq():
    global _groq_client
    key = _get_key("groq")
    if not key:
        return None
    try:
        from openai import OpenAI
        _groq_client = OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")
        return (_groq_client, key)
    except Exception as e:
        logger.error(f"Groq init error: {e}")
        return None


MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
]

OPENROUTER_MODELS = [
    "nousresearch/hermes-3-llama-3.1-405b",
    "nousresearch/hermes-2-pro-mistral-7b",
    "nousresearch/hermes-2-theta-llama-3-8b",
    "qwen/qwen-2.5-coder-32b-instruct",
    "deepseek/deepseek-chat",
    "google/gemma-2-27b-it",
]

CODE_MODELS = [
    "nousresearch/hermes-3-llama-3.1-405b",
    "qwen/qwen-2.5-coder-32b-instruct",
    "deepseek/deepseek-coder",
    "cognitivecomputations/dolphin-2.9.3-qwen2-72b",
]


def _get_openrouter():
    key = _get_key("openrouter")
    if not key:
        return None
    try:
        from openai import OpenAI
        return (OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1"), key)
    except:
        return None


def _call_groq(client, model: str, messages: list, pool, key: str = None) -> str:
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=256,
            temperature=1.0,
            frequency_penalty=1.0,
            presence_penalty=0.8
        )
        if key:
            pool.record_success(key)
        return resp.choices[0].message.content.strip() or "پاسخی دریافت نشد."
    except Exception as e:
        err_str = str(e)
        logger.warning(f"{pool.name} {model} failed: {err_str[:100]}")
        err_type = classify_error(err_str)
        if key:
            pool.record_failure(key, err_type)
        if any(k in err_str for k in ["413", "Payload Too Large", "402", "context length", "token limit", "tokens limit exceeded"]):
            return "⚠CONTEXT_OVERFLOW"
        if err_type == "auth_fail":
            return "⚠AUTH_FAIL"
        if err_type == "rate_limit":
            return "⚠RATE_LIMIT"
        return None


def _call_google(user_message: str, system_prompt: str, chat_history: list = None) -> str:
    result = _get_google()
    if not result:
        return None
    client, key = result
    try:
        full_prompt = f"{system_prompt}\n\n{user_message}"
        resp = client.models.generate_content(model="gemini-2.0-flash", contents=full_prompt)
        gemini_pool.record_success(key)
        return resp.text.strip() or "پاسخی دریافت نشد."
    except Exception as e:
        err_str = str(e)[:200]
        logger.warning(f"Gemini failed: {err_str[:100]}")
        gemini_pool.record_failure(key, classify_error(err_str))
        return None


def _call_deepseek(user_message: str, system_prompt: str, chat_history: list = None) -> str:
    result = _get_groq()
    if not result:
        return None
    client, key = result
    messages = [{"role": "system", "content": system_prompt}]
    if chat_history:
        for msg in chat_history[-6:]:
            role = "user" if msg.get("role") == "user" else "assistant"
            messages.append({"role": role, "content": msg.get("content", "")})
    messages.append({"role": "user", "content": user_message})
    for model in MODELS:
        result = _call_groq(client, model, messages, groq_pool, key)
        if result is not None and not result.startswith("⚠"):
            return result
    or_result = _get_openrouter()
    if or_result:
        or_client, or_key = or_result
        for model in OPENROUTER_MODELS:
            result = _call_groq(or_client, model, messages, openrouter_pool, or_key)
            if result is not None and not result.startswith("⚠"):
                return result
    return None


async def web_search(query: str, max_results: int = 5) -> str:
    try:
        import warnings
        warnings.filterwarnings("ignore", message=".*duckduckgo_search.*")
        from duckduckgo_search import DDGS
        results = []
        def _search():
            with DDGS() as ddgs:
                for r in ddgs.text(query, max_results=max_results):
                    results.append(r)
        await asyncio.to_thread(_search)
        if not results:
            return "نتیجه‌ای پیدا نشد."
        lines = []
        for i, r in enumerate(results, 1):
            title = r.get("title", "").strip()
            body = r.get("body", "").strip()
            if title or body:
                lines.append(f"{i}. {title}\n   {body[:200]}")
        return "\n\n".join(lines) if lines else "نتیجه‌ای پیدا نشد."
    except Exception as e:
        logger.error(f"web_search error: {e}")
        return ""


async def ask_ai(user_message: str, system_prompt: str = None, chat_history: list = None, user_memory: str = "", qa_context: list = None, fallback_prompt: str = None) -> str:
    prompt = system_prompt or DEFAULT_PROMPT
    if qa_context:
        ctx = "\n".join([f"Q: {p['question']}\nA: {p['answer']}" for p in qa_context[-3:]])
        prompt += f"\n\n[تجربه قبلی من در این گروه:\n{ctx}]"
    if user_memory:
        prompt += f"\n\n[حافظه من از این کاربر: {user_memory}]"

    cached = await cache.get_ai_response(user_message, prompt)
    if cached:
        cached = re.split(r'[.!?\n]', cached)[0].strip()
        if len(cached) > 60:
            cached = cached[:57] + "..."
        return cached

    # Build prompt tiers
    try:
        from handlers.personality_core import build_micro_prompt
        micro_prompt = build_micro_prompt()
    except Exception:
        micro_prompt = ""
    lite_prompt = fallback_prompt if fallback_prompt and fallback_prompt != prompt else ""
    full_prompt = prompt + SEARCH_INSTRUCTION

    tiers = {"full": full_prompt, "lite": lite_prompt, "micro": micro_prompt}

    def _call_with_tier(provider: str, model: str, tier: str) -> str | None:
        tier_text = tiers.get(tier)
        if not tier_text:
            return None
        if provider == "gemini":
            return _call_google(user_message, tier_text, chat_history)
        sender_fn = _call_deepseek if provider == "groq" else None
        if provider == "openrouter":
            or_r = _get_openrouter()
            if not or_r:
                return None
            or_client, or_key = or_r
            hist_count = 6 if tier == "full" else (2 if tier == "lite" else 1)
            msgs = [{"role": "system", "content": tier_text}]
            if chat_history:
                for msg in chat_history[-hist_count:]:
                    role = "user" if msg.get("role") == "user" else "assistant"
                    msgs.append({"role": role, "content": msg.get("content", "")})
            msgs.append({"role": "user", "content": user_message})
            return _call_groq(or_client, model, msgs, openrouter_pool, or_key)
        return None

    # Pre-flight: for each model, find best tier and call once
    response = None
    chain = []
    if gemini_pool.keys:
        chain.append(("gemini", "gemini-2.0-flash"))
    chain.append(("groq", "llama-3.3-70b-versatile"))
    for m in OPENROUTER_MODELS:
        chain.append(("openrouter", m))

    for provider, model in chain:
        overhead = 0
        if chat_history:
            overhead = sum(len(m.get("content", "")) for m in chat_history[-6:]) // 4
        tier = best_tier(model, tiers, overhead)
        if not tier:
            continue
        logger.debug(f"ask_ai: {provider}/{model} -> {tier} tier")
        response = await asyncio.to_thread(_call_with_tier, provider, model, tier)
        if response and not response.startswith(("⚠", "⏳")):
            break
        response = None

    if not response:
        return "⚠️ خطا: همه مدل‌ها محدودیت دارن. بعداً امتحان کن."

    if response.startswith("SEARCH:"):
        query = response[len("SEARCH:"):].strip()
        logger.info(f"AI requested search: {query}")
        search_results = await web_search(query)
        if search_results:
            search_context = SEARCH_PROMPT_TEMPLATE.format(query=query, results=search_results)
            response = await asyncio.to_thread(_call_google, user_message + f"\n\n{search_context}", prompt + SEARCH_INSTRUCTION, chat_history)
            if not response:
                response = await asyncio.to_thread(_call_deepseek, user_message + f"\n\n{search_context}", prompt + SEARCH_INSTRUCTION, chat_history)
            if not response:
                response = "⚠️ خطا: همه مدل‌ها محدودیت دارن. بعداً امتحان کن."
        else:
            response = await asyncio.to_thread(_call_google, user_message, prompt + SEARCH_INSTRUCTION, chat_history)
            if not response:
                response = await asyncio.to_thread(_call_deepseek, user_message, prompt + SEARCH_INSTRUCTION, chat_history)
            if not response:
                response = "⚠️ خطا: همه مدل‌ها محدودیت دارن. بعداً امتحان کن."

    if not response.startswith("⚠") and not response.startswith("⏳"):
        await cache.cache_ai_response(user_message, prompt, response)
    response = re.split(r'[.!?\n]', response)[0].strip()
    if len(response) > 60:
        response = response[:57] + "..."
    return response


def split_sentences(text: str) -> list[str]:
    parts = re.split(r'(?<=[.!?؟\n])\s*', text)
    return [p.strip() for p in parts if p.strip()]


async def generate_image(prompt: str) -> str:
    import httpx
    url = f"https://image.pollinations.ai/prompt/{prompt}?width=1024&height=1024&nologo=true"
    return url


CODE_SYSTEM = (
    "تو یه برنامه‌نویس حرفه‌ای و کمک‌حال کدنویسی هستی. "
    "به سوالات برنامه‌نویسی پاسخ کامل و دقیق بده. "
    "کد رو با توضیح بفرست. "
    "زبان پاسخ فارسی باشه ولی کد به انگلیسی."
)


async def ask_code(user_message: str, chat_history: list = None) -> str:
    prompt = CODE_SYSTEM
    response = await ask_ai(user_message, prompt, chat_history)
    if response.startswith("⚠"):
        or_result = _get_openrouter()
        if or_result:
            or_client, or_key = or_result
            messages = [{"role": "system", "content": CODE_SYSTEM}]
            if chat_history:
                for msg in chat_history[-4:]:
                    role = "user" if msg.get("role") == "user" else "assistant"
                    messages.append({"role": role, "content": msg.get("content", "")})
            messages.append({"role": "user", "content": user_message})
            for model in CODE_MODELS:
                result = _call_groq(or_client, model, messages, openrouter_pool, or_key)
                if result is not None:
                    return result
    return response


MEMORY_EXTRACT_PROMPT = (
    "کاربر این حرف رو زده: «{message}» و من (کتلت) این جواب رو دادم: «{response}». "
    "حافظه قبلی من از این کاربر: {old_memory}\n\n"
    "از این گفتگو چه نکته مهمی باید درباره کاربر به خاطر بسپارم؟ "
    "فقط خلاصه رو بگو، حداکثر ۲ خط. اگه نکته جدیدی نیست، بگو: هیچ"
)


async def extract_memory(user_message: str, response: str, old_memory: str = "") -> str:
    try:
        prompt_text = MEMORY_EXTRACT_PROMPT.format(message=user_message[:200], response=response[:200], old_memory=old_memory or "هیچ")
        if gemini_pool.keys:
            extracted = await asyncio.to_thread(_call_google, prompt_text, "تو یه سیستم هستی که حافظه کاربر رو خلاصه میکنی. مختصر و مفید جواب بده.")
        else:
            extracted = await asyncio.to_thread(_call_deepseek, prompt_text, "تو یه سیستم هستی که حافظه کاربر رو خلاصه میکنی. مختصر و مفید جواب بده.")
        if not extracted:
            return old_memory
        extracted = extracted.strip()
        if not extracted or extracted == "هیچ" or len(extracted) < 5:
            return old_memory
        if old_memory:
            combined = f"{old_memory} | {extracted}"
            if len(combined) > 500:
                combined = combined[:500]
            return combined
        return extracted[:500]
    except:
        return old_memory
