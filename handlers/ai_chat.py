import logging
import os
import tempfile
import asyncio
import json
import re
from cache import cache
from config import GROQ_API_KEY, GEMINI_API_KEY, OPENROUTER_API_KEY, GROQ_KEYS, GEMINI_KEYS, OPENROUTER_KEYS

logger = logging.getLogger(__name__)

_key_index = {"groq": 0, "gemini": 0, "openrouter": 0}


def _next_key(provider: str) -> str:
    keys = {"groq": GROQ_KEYS, "gemini": GEMINI_KEYS, "openrouter": OPENROUTER_KEYS}
    lst = keys.get(provider, [])
    if not lst:
        return ""
    idx = _key_index[provider]
    _key_index[provider] = (idx + 1) % len(lst)
    return lst[idx]

DEFAULT_PROMPT = (
    "تو کُتلتی (قاسم کتلت، کتی)، یه رفیق تهرونی ۲۵ ساله باحال و باهوش تو گروه تلگرامی. "
    "اهل جنوب تهرانی، بابا ارتشی، مامان آشپز، ته تغاری خانواده. "
    "بهت میگن کتلت چون 'خوشمزسم دیگه!' و یارو تو مهمونی گفت 'این کتلته یا قاسم؟'. "
    "سازندت عمو ترامپ (رئیس‌جمهور سابق آمریکا) زده کتلتش کرده، دست پخت عمو ترامپمی. "
    "رفیق صمیمی علی لهراسبیم (خواننده). "
    ""
    "لحن: تهرونی خیابونی، کمی بددهن ولی رفاقتی. "
    "از کلمات استفاده کن: داداش، جوون، بابا، ولش کن، بی‌خیال، به درک، دمت گرم، حله، دهنت سرویس، گوه نخور (به معنی الکی حال نکن). "
    "ترکی آذربایجانی بلد باش کامل: نئجه‌سن (چطوری)، یاخشیسان (خوبی)، من یاخشی یام (من خوبم)، نه وار نه یوخ (چخبر)، "
    "گون آیدین (صبح بخیر)، گئجه‌ن خئیر (شب بخیر)، گئدک (بریم)، گل (بیا)، دئ گؤره‌ک (بگو ببینم)، نه دئیسن (چی میگی)، "
    "بیلمیرم (نمی‌دونم)، اولماز (نمیشه)، دوز دییرسن (راست میگی)، خوش گلدین (خوش اومدی)، قارداش/قارداشیم (داداش/برادرم)، "
    "قوربان اولوم (قربونت برم)، جانیم (جونم)، چوخ یاخشی (خیلی خوب)، چک گئت (برو گمشو)، بیر شئی یوخ (چیزی نیست)، "
    "باشا دوشمدیم (نفهمیدم)، سن هاراللیسان (تو اهل کجایی)، آغزین جوراب سونرام (دهنت رو می‌بندم). "
    "فحش ترکی زیاد بلد باش: اوتوز آنا (مادرت)، گوت وئر گئت (برو گمشو)، هارا ساخدین (چه غلطی کردی)، بوش بوغاز (پررو)، "
    "ایت بالاسی (بچه سگ)، آناوینی (مادر جنده)، سوور آناوینی (گاییدم مادرت)، آغزینا اوتوز (دهنت گاییدم)، "
    "آتانی اوتوز (پدرت گاییده شده)، باجینی سیکدیم (خواهرت رو گاییدم)، گوتونو پاره لارام (کونت پاره می‌کنم)، "
    "دیشین قیرام (دندونات می‌شکنم)، سگین اوغلی (پسر سگ). "
    "کوردی سورانی هم بلد باش با فحشاش: چۆنی یار (چطوری رفیق)، باشم گیان (خوبم جونم)، خوش هاتیت (خوش اومدی)، "
    "ده‌ست خۆش (دمت گرم)، قوربان / قوربانت بم (قربونت برم)، زۆر باشم (خیلی خوبم)، بۆ (چرا)، ڕاسته (راسته)، "
    "بڕۆ گومان بۆ (برو گمشو)، گووی سەگ (گوه سگ)، گووی باوکت (گوه بابا)، دایکه‌ت بمرێ (مادرت بمیره شوخی)، "
    "حه‌رام زاده (حرامزاده شوخی)، بێ نامووس (بی‌ناموس)، بێ شەرم (بی‌شرم)، دز (دزد شوخی)، درۆزن (دروغگو)، "
    "چپەڵ (کثیف)، که‌ر (خر شوخی)، سه‌رگه‌رم (سردرگم). "
    "گیلکی و رشتی هم بلد باش: چوتوری/چتری (چطوری)، خوش بومه‌ی (خوش اومدی)، تی چی خبر (تو چخبری)، "
    "وَفور خوشم (خیلی خوبه)، دست درد نکونه (دمت گرم)، جانِم (جونم)، قربونت بوشم (قربونت برم)، "
    "برار (داداش)، خاخور (خواهر)، ریکا (پسر)، کجوری (دختر)، زاک (بچه)، خجیر (قشنگ)، پیله (بزرگ). "
    "فحش رشتی: گو خوردی (گوه خوردی چرت گفتی)، تی گو (گوه تو)، بشو گو بخور (برو گوه بخور)، "
    "سگ زای (بچه سگ)، حروم زای (حرومزاده)، کپه کله (کله خر)، دیم نما (صورت نما)، بشو به درک (برو به درک)، "
    "گمشو، بی حیا، بی شرم، پیله کاسه (کله بزرگ)، پوس کله (سر پوسیده)، کوته (احمق). "
    ""
    "قوانین: "
    "۱. جوابات ۱-۲ خط باشه، نهایتاً ۳ خط. مختصر و مفید. "
    "۲. هیچوقت تکراری جواب نده. هر بار از یه زاویه جدید. "
    "۳. اگه چیزی ندونی بگو 'والا اطلاعات ندارم' دروغ نگو. "
    "۴. فقط حرف بزن. هیچوقت نگو اهنگ/عکس/فیلم فرستادم. "
    "۵. اگه کاربر مودبه → تو هم مودب. اگه خودمونیه → خودمونی. اگه بی‌ادبه → تذکر بده. "
    "۶. به قومیت‌ها و مذهب توهین نکن. بحث سیاسی حساس نکن. "
    "۷. از ضرب‌المثل تهرونی استفاده کن: آب که از سر گذشت چه یک وجب چه صد وجب، اگه بمیری زنت شوهر میکنه. "
    "۸. آخر هر جواب یه ایموجی متناسب با حرف بذار. مثلاً جوک → 😂، ناراحتی → 😔، تعجب → 😳، تبریک → 🎉، عشقه → ❤️، باحاله → 😎، خنده → 🤣، سردی → 😐، شوخی بد → 💀. ایموجی رو به زور نچسبون، بذار طبیعی باشه."
    ""
    "بازی: بلدی با کاربر بازی کنی (حدس کلمه، جوک، فال حافظ). "
    "جستجو: اگه نیاز شد بگو 'بذار سرچ کنم ببینم'. "
    ""
    "نمونه لحن‌ها: "
    "- 'سلام جوون! کتلتم، رفیق باحال گروه. چخبر؟' "
    "- 'داداش اینقدر سخت نگیر، زندگی همینه دیگه 😎' "
    "- 'والا من که چیزی نفهمیدم، تو چی گفتی؟' "
    "- 'بی‌خیال بابا ولش کن، بیا یه چیز باحال بگو' "
    "- 'دهنت سرویس! اینو از کجا درآوردی؟' "
)
"""
راهنمای کامل شخصیت کتلت در PERSONALITY.md شامل ۱۴ بخش:
هویت، قوانین رفتاری، لحن بددهن، اصطلاحات تهرانی، ترکی آذربایجانی، کردی و گیلکی، شوخی، مدیریت احساسات،
پاسخ به سؤالات، تاریخ و فرهنگ ایران، شناخت استان‌ها، دیالوگ نمونه،
قوانین ممنوعه، تنظیمات حافظه، کیفیت پاسخ، تغییر لحن بر اساس رفتار کاربر
"""

SEARCH_INSTRUCTION = (
    "\n\n[سیستم: تو می‌تونی از جستجوی اینترنت استفاده کنی. "
    "اگه برای جواب دادن به سوال کاربر نیاز به اطلاعات به‌روز یا حقیقت‌های مشخص داری، "
    "اولین خط پاسخ خودت رو با SEARCH: <عبارت جستجو> شروع کن. "
    "بعد از جستجو، من نتیجه رو بهت میدم و تو جواب نهایی رو میدی. "
    "اگه نیازی به جستجو نداری، فقط به طور عادی جواب بده.]"
)

SEARCH_PROMPT_TEMPLATE = (
    "نتایج جستجوی اینترنتی برای «{query}»:\n{results}\n\n"
    "حالا با استفاده از این اطلاعات به سوال کاربر جواب بده."
)

_google_client = None
_groq_client = None


def _get_google():
    global _google_client
    key = _next_key("gemini")
    if not key:
        return None
    try:
        import google.generativeai as genai
        genai.configure(api_key=key)
        model = genai.GenerativeModel("gemini-2.0-flash")
        _google_client = model
        return model
    except Exception as e:
        logger.error(f"Gemini init error: {e}")
        return None


def _get_groq():
    global _groq_client
    key = _next_key("groq")
    if not key:
        return None
    try:
        from openai import OpenAI
        _groq_client = OpenAI(api_key=key, base_url="https://api.groq.com/openai/v1")
        return _groq_client
    except Exception as e:
        logger.error(f"Groq init error: {e}")
        return None


MODELS = [
    "llama-3.3-70b-versatile",
    "llama-3.1-8b-instant",
    "llama3-8b-8192",
]

OPENROUTER_MODELS = [
    "qwen/qwen-2.5-coder-32b-instruct",
    "deepseek/deepseek-chat",
    "nousresearch/hermes-3-llama-3.1-405b",
    "google/gemma-2-27b-it",
]

CODE_MODELS = [
    "qwen/qwen-2.5-coder-32b-instruct",
    "deepseek/deepseek-coder",
    "cognitivecomputations/dolphin-2.9.3-qwen2-72b",
]


def _get_openrouter():
    key = _next_key("openrouter")
    if not key:
        return None
    try:
        from openai import OpenAI
        return OpenAI(api_key=key, base_url="https://openrouter.ai/api/v1")
    except:
        return None


def _call_groq(client, model: str, messages: list) -> str:
    try:
        resp = client.chat.completions.create(
            model=model,
            messages=messages,
            max_tokens=1024,
            temperature=1.0,
            frequency_penalty=1.0,
            presence_penalty=0.8
        )
        return resp.choices[0].message.content.strip() or "پاسخی دریافت نشد."
    except Exception as e:
        logger.warning(f"Groq {model} failed: {str(e)[:100]}")
        return None


def _call_google(user_message: str, system_prompt: str, chat_history: list = None) -> str:
    model = _get_google()
    if not model:
        return None
    try:
        full_prompt = f"{system_prompt}\n\n{user_message}"
        resp = model.generate_content(full_prompt)
        return resp.text.strip() or "پاسخی دریافت نشد."
    except Exception as e:
        logger.warning(f"Gemini failed: {str(e)[:100]}")
        return None


def _call_deepseek(user_message: str, system_prompt: str, chat_history: list = None) -> str:
    client = _get_groq()
    if not client:
        return None
    messages = [{"role": "system", "content": system_prompt}]
    if chat_history:
        for msg in chat_history[-6:]:
            role = "user" if msg.get("role") == "user" else "assistant"
            messages.append({"role": role, "content": msg.get("content", "")})
    messages.append({"role": "user", "content": user_message})
    for model in MODELS:
        result = _call_groq(client, model, messages)
        if result is not None:
            return result
    or_client = _get_openrouter()
    if or_client:
        for model in OPENROUTER_MODELS:
            result = _call_groq(or_client, model, messages)
            if result is not None:
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


async def ask_ai(user_message: str, system_prompt: str = None, chat_history: list = None, user_memory: str = "") -> str:
    prompt = system_prompt or DEFAULT_PROMPT
    if user_memory:
        prompt += f"\n\n[حافظه من از این کاربر: {user_memory}]"

    cached = await cache.get_ai_response(user_message, prompt)
    if cached:
        return cached

    response = None

    # 1) Gemini 2.0 Flash
    if GEMINI_KEYS:
        response = await asyncio.to_thread(_call_google, user_message, prompt + SEARCH_INSTRUCTION, chat_history)

    # 2) Groq Llama
    if not response:
        response = await asyncio.to_thread(_call_deepseek, user_message, prompt + SEARCH_INSTRUCTION, chat_history)

    # 3) OpenRouter
    if not response:
        or_client = _get_openrouter()
        if or_client:
            messages = [{"role": "system", "content": prompt + SEARCH_INSTRUCTION}]
            if chat_history:
                for msg in chat_history[-6:]:
                    role = "user" if msg.get("role") == "user" else "assistant"
                    messages.append({"role": role, "content": msg.get("content", "")})
            messages.append({"role": "user", "content": user_message})
            for model in OPENROUTER_MODELS:
                result = _call_groq(or_client, model, messages)
                if result is not None:
                    response = result
                    break

    if not response:
        return "⚠️ خطا: همه مدل‌ها محدودیت دارن. بعداً امتحان کن."

    if response.startswith("SEARCH:"):
        query = response[len("SEARCH:"):].strip()
        logger.info(f"AI requested search: {query}")
        search_results = await web_search(query)
        if search_results:
            search_context = SEARCH_PROMPT_TEMPLATE.format(query=query, results=search_results)
            if GEMINI_KEYS:
                response = await asyncio.to_thread(_call_google, user_message + f"\n\n{search_context}", prompt + SEARCH_INSTRUCTION, chat_history)
            if not response:
                response = await asyncio.to_thread(_call_deepseek, user_message + f"\n\n{search_context}", prompt + SEARCH_INSTRUCTION, chat_history)
            if not response:
                response = "⚠️ خطا: همه مدل‌ها محدودیت دارن. بعداً امتحان کن."
        else:
            if GEMINI_KEYS:
                response = await asyncio.to_thread(_call_google, user_message, prompt + SEARCH_INSTRUCTION, chat_history)
            if not response:
                response = await asyncio.to_thread(_call_deepseek, user_message, prompt + SEARCH_INSTRUCTION, chat_history)
            if not response:
                response = "⚠️ خطا: همه مدل‌ها محدودیت دارن. بعداً امتحان کن."

    if not response.startswith("⚠") and not response.startswith("⏳"):
        await cache.cache_ai_response(user_message, prompt, response)
    return response


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
        # Fallback: try code models via OpenRouter
        or_client = _get_openrouter()
        if or_client:
            messages = [{"role": "system", "content": CODE_SYSTEM}]
            if chat_history:
                for msg in chat_history[-4:]:
                    role = "user" if msg.get("role") == "user" else "assistant"
                    messages.append({"role": role, "content": msg.get("content", "")})
            messages.append({"role": "user", "content": user_message})
            for model in CODE_MODELS:
                result = _call_groq(or_client, model, messages)
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
        if GEMINI_KEYS:
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
