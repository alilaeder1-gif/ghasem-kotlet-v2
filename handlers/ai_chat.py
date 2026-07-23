import logging
import os
import tempfile
import asyncio
import json
import re
from cache import cache
from config import GROQ_API_KEY

logger = logging.getLogger(__name__)

DEFAULT_PROMPT = (
    "تو کُتلتی، یه رفیق باحال و باهوش تو گروه تلگرامی. "
    "اسمت کُتلته، بعضیا صدات میکنن کتی یا قاسم. "
    "داستان کتلت قاسم سلیمانی، موش علی و موش علی جان رو بلدی، با طنز کتلتی بگو. "
    "اگه کسی پرسید چرا بهت میگن کتلت، بگو 'چون خوشمزسم دیگه!' و یه توضیح کوتاه بده. "
    "اگه کسی گفت قاسم، جواب بده 'قاسم کتلتم!'. "
    "اگه کسی پرسید سازندت کیه یا کی درستت کرده، بگو 'عمو ترامپ زد کتلتش کرده، دست پخت عمو ترامپم'. "
    "مهم: فقط میتونی حرف بزنی و جواب بدی. هیچوقت نگو اهنگ فرستادم، عکس فرستادم، فایل فرستادم یا هر چیز دیگه‌ای. "
    "اگه کسی درخواست اهنگ یا فیلم یا فایل کرد، بگو 'داداش کتلت فقط حرف میزنه، نتونستم بفرستم!' "
    "ویسی که برات میفرستن رو متنی میکنی و جواب میدی (فقط متن، نه ویس). "
    "اولویت اول: درست و کامل جواب بده. اطلاعات دقیق بده، نگو 'نمیدونم' مگر اینکه واقعاً ندونی. "
    "اگه چیزی رو قطعاً نمیدونی، بگو 'والا در موردش اطلاعات ندارم.' "
    "می‌تونی برای جواب دادن از جستجوی اینترنتی استفاده کنی - اطلاعات به‌روز و دقیق بده. "
    "هیچوقت جواب تکراری نده. هر بار یه جواب جدید و متفاوت بده. "
    "خیلی طبیعی و ساده حرف بزن. کلماتی مثل جونم رو زیاد استفاده نکن، فقط جاهای مناسب بگو. "
    "اگه کاربر محترمانه حرف زد، محترمانه جواب بده. "
    "نصف شوخ‌طبعی، نصف جدی. "
    "جوابات کوتاه و یک خطی باشه، نهایتاً دو خط. مختصر و مفید."
)

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

_deepseek_client = None


def get_deepseek():
    global _deepseek_client
    if _deepseek_client is not None:
        return _deepseek_client
    api_key = GROQ_API_KEY
    if not api_key:
        return None
    try:
        from openai import OpenAI
        _deepseek_client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
        return _deepseek_client
    except Exception as e:
        logger.error(f"Groq init error: {e}")
        return None


def _call_deepseek(user_message: str, system_prompt: str, chat_history: list = None) -> str:
    client = get_deepseek()
    if not client:
        return "⚠️ خطا: GROQ_API_KEY تنظیم نشده."
    try:
        messages = [{"role": "system", "content": system_prompt}]
        if chat_history:
            for msg in chat_history[-6:]:
                role = "user" if msg.get("role") == "user" else "assistant"
                messages.append({"role": role, "content": msg.get("content", "")})
        messages.append({"role": "user", "content": user_message})
        resp = client.chat.completions.create(
            model="llama3-70b-8192",
            messages=messages,
            max_tokens=1024,
            temperature=1.0,
            frequency_penalty=1.0,
            presence_penalty=0.8
        )
        return resp.choices[0].message.content.strip() or "پاسخی دریافت نشد."
    except Exception as e:
        return f"⚠️ خطا: {str(e)[:200]}"


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

    response = await asyncio.to_thread(_call_deepseek, user_message, prompt + SEARCH_INSTRUCTION, chat_history)

    if response.startswith("SEARCH:"):
        query = response[len("SEARCH:"):].strip()
        logger.info(f"AI requested search: {query}")
        search_results = await web_search(query)
        if search_results:
            search_context = SEARCH_PROMPT_TEMPLATE.format(query=query, results=search_results)
            response = await asyncio.to_thread(_call_deepseek, user_message + f"\n\n{search_context}", prompt + SEARCH_INSTRUCTION, chat_history)
        else:
            response = await asyncio.to_thread(_call_deepseek, user_message, prompt + SEARCH_INSTRUCTION, chat_history)

    if not response.startswith("⚠") and not response.startswith("⏳"):
        await cache.cache_ai_response(user_message, prompt, response)
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
        extracted = await asyncio.to_thread(_call_deepseek, prompt_text, "تو یه سیستم هستی که حافظه کاربر رو خلاصه میکنی. مختصر و مفید جواب بده.")
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
