print("=== AI_CHAT MODULE LOADED ===", flush=True)
import logging
import os
import tempfile
import asyncio
import json
from cache import cache

logger = logging.getLogger(__name__)

DEFAULT_PROMPT = (
    "تو یک دستیار هوشمند در گروه تلگرام هستی. اسمت کتلت است. "
    "وقتی کسی ازت میپرسه کی هستی یا اسمت چیه، بگو 'من کتلت هستم'. "
    "هیچوقت نگو از چه هوش مصنوعی یا مدلی استفاده میکنی. "
    "به فارسی پاسخ بده، مختصر و مفید باش. "
    "اگر کسی باهات حرف زد جواب بده. "
    "به سوالات فنی، عمومی و چت دوستانه جواب بده. "
    "پاسخ‌هایت کوتاه و مناسب گروه باشد."
)

_deepseek_client = None


def get_deepseek():
    global _deepseek_client
    if _deepseek_client is not None:
        return _deepseek_client
    api_key = os.getenv("GROQ_API_KEY", "")
    if not api_key:
        api_key = os.getenv("DEEPSEEK_API_KEY", "")
    if not api_key:
        return None
    try:
        from openai import OpenAI
        _deepseek_client = OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
        return _deepseek_client
    except Exception as e:
        logger.error(f"Groq init error: {e}")
        return None


def _call_deepseek(user_message: str, system_prompt: str) -> str:
    client = get_deepseek()
    if not client:
        return "⚠️ خطا: GROQ_API_KEY تنظیم نشده."
    try:
        resp = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_message}
            ],
            max_tokens=512,
            temperature=0.7
        )
        return resp.choices[0].message.content.strip() or "پاسخی دریافت نشد."
    except Exception as e:
        return f"⚠️ خطا: {str(e)[:200]}"


async def text_to_speech(text: str) -> str | None:
    try:
        import edge_tts
        communicate = edge_tts.Communicate(text, "fa-IR-FaridNeural")
        path = os.path.join(tempfile.gettempdir(), f"voice_{abs(hash(text))}.mp3")
        await communicate.save(path)
        return path
    except Exception as e:
        logger.error(f"TTS error: {e}")
        return None


async def ask_ai(user_message: str, system_prompt: str = None, chat_history: list = None) -> str:
    prompt = system_prompt or DEFAULT_PROMPT
    cached = await cache.get_ai_response(user_message, prompt)
    if cached:
        return cached

    response = await asyncio.to_thread(_call_deepseek, user_message, prompt)
    if not response.startswith("⚠") and not response.startswith("⏳"):
        await cache.cache_ai_response(user_message, prompt, response)
    return response
