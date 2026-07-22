print("=== AI_CHAT MODULE LOADED ===", flush=True)
import logging
import os
import tempfile
import asyncio
import json
from config import HUGGINGFACE_API_KEY, AI_MODEL
from database import db
from cache import cache

logger = logging.getLogger(__name__)

DEFAULT_PROMPT = (
    "تو یک دستیار هوشمند در گروه تلگرام هستی. "
    "به فارسی پاسخ بده، مختصر و مفید باش. "
    "اگر کسی باهات حرف زد جواب بده. "
    "به سوالات فنی، عمومی و چت دوستانه جواب بده. "
    "پاسخ‌هایت کوتاه و مناسب گروه باشد."
)


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


async def _call_huggingface_async(url: str, headers: dict, payload: dict) -> str:
    import httpx
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(url, headers=headers, json=payload)
            if resp.status_code == 200:
                data = resp.json()
                if isinstance(data, list) and data:
                    text = data[0].get("generated_text", "")
                    return text or "پاسخی دریافت نشد."
                elif isinstance(data, dict):
                    return data.get("generated_text", "پاسخی دریافت نشد.")
                return f"⚠️ خطا: {str(data)[:200]}"
            elif resp.status_code == 503:
                return "⏳ مدل در حال بارگذاری است، لطفاً چند لحظه صبر کنید."
            else:
                return f"⚠️ خطا: {resp.status_code} - {resp.text[:200]}"
    except Exception as e:
        return f"⚠️ خطا در اتصال: {str(e)[:200]}"


async def ask_ai(user_message: str, system_prompt: str = None, chat_history: list = None) -> str:
    if not HUGGINGFACE_API_KEY:
        return "⚠️ کلید API تنظیم نشده. لطفاً HUGGINGFACE_API_KEY رو در فایل .env تنظیم کنید."

    prompt = system_prompt or DEFAULT_PROMPT
    cached = await cache.get_ai_response(user_message, prompt)
    if cached:
        return cached

    messages_list = [{"role": "system", "content": prompt}]
    if chat_history:
        messages_list.extend(chat_history[-6:])
    messages_list.append({"role": "user", "content": user_message})

    chat_prompt = format_llama3_prompt(messages_list)
    url = f"https://api-inference.huggingface.co/models/{AI_MODEL}"
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
    payload = {
        "inputs": chat_prompt,
        "parameters": {
            "max_new_tokens": 512,
            "temperature": 0.7,
            "return_full_text": False
        }
    }

    urls = [
        f"https://router.huggingface.co/hf-inference/models/{AI_MODEL}",
        f"https://api-inference.huggingface.co/models/{AI_MODEL}",
    ]

    last_error = None
    for url in urls:
        response = await _call_huggingface_async(url, headers, payload)
        if not response.startswith("⚠"):
            break
        last_error = response
    else:
        response = last_error
    if not response.startswith("⚠") and not response.startswith("⏳"):
        await cache.cache_ai_response(user_message, prompt, response)
    return response


def format_llama3_prompt(messages: list) -> str:
    formatted = "<|begin_of_text|>"
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        formatted += f"<|start_header_id|>{role}<|end_header_id|>\n\n{content}<|eot_id|>"
    formatted += "<|start_header_id|>assistant<|end_header_id|>\n\n"
    return formatted


def format_chat_prompt(messages: list) -> str:
    formatted = ""
    for msg in messages:
        role = msg["role"]
        content = msg["content"]
        if role == "system":
            formatted += f"<|system|>\n{content}\n"
        elif role == "user":
            formatted += f"<|user|>\n{content}\n"
        elif role == "assistant":
            formatted += f"<|assistant|>\n{content}\n"
    formatted += "<|assistant|>\n"
    return formatted
