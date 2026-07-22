import aiohttp
import logging
import os
import tempfile
import asyncio
from aiogram import Router, F
from aiogram.types import Message, FSInputFile
from config import HUGGINGFACE_API_KEY, AI_MODEL
from database import db
from cache import cache

logger = logging.getLogger(__name__)

router = Router()

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


async def ask_ai(user_message: str, system_prompt: str = None, chat_history: list = None) -> str:
    if not HUGGINGFACE_API_KEY:
        return "⚠️ کلید API تنظیم نشده. لطفاً HUGGINGFACE_API_KEY رو در فایل .env تنظیم کنید."

    cached = await cache.get_ai_response(user_message, system_prompt or DEFAULT_PROMPT)
    if cached:
        return cached

    prompt = system_prompt or DEFAULT_PROMPT
    messages_list = [{"role": "system", "content": prompt}]
    if chat_history:
        messages_list.extend(chat_history[-6:])
    messages_list.append({"role": "user", "content": user_message})

    url = f"https://api-inference.huggingface.co/models/{AI_MODEL}"
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
    payload = {"inputs": format_chat_prompt(messages_list), "parameters": {"max_new_tokens": 512, "temperature": 0.7, "return_full_text": False}}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                body = await resp.text()
                if resp.status == 200:
                    import json
                    data = json.loads(body)
                    if isinstance(data, list) and data:
                        response = data[0].get("generated_text", "پاسخی دریافت نشد.")
                    elif isinstance(data, dict):
                        response = data.get("generated_text", "پاسخی دریافت نشد.")
                    else:
                        response = "پاسخی دریافت نشد."
                    await cache.cache_ai_response(user_message, prompt, response)
                    return response
                elif resp.status == 503:
                    return "⏳ مدل در حال بارگذاری است، لطفاً چند لحظه صبر کنید."
                else:
                    return f"⚠️ خطا: {resp.status} - {body[:200]}"
    except Exception as e:
        return f"⚠️ خطا در اتصال: {str(e)[:150]}"


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


@router.message()
async def ai_chat_handler(message: Message):
    user_msg = (message.text or message.caption or "").strip()
    logger.info(f"ai_chat_handler called: chat_type={message.chat.type}, has_text={bool(user_msg)}")

    if not user_msg or user_msg.startswith("/"):
        return

    if message.chat.type in ("group", "supergroup"):
        bot_info = await message.bot.get_me()
        bot_username = bot_info.username
        is_mention = bot_username and f"@{bot_username}" in user_msg
        is_reply = (
            message.reply_to_message
            and message.reply_to_message.from_user
            and message.reply_to_message.from_user.id == bot_info.id
        )
        if not is_mention and not is_reply:
            return
        if is_mention:
            user_msg = user_msg.replace(f"@{bot_username}", "").strip()

    if not user_msg:
        user_msg = "سلام"

    persona = await db.get_persona(message.chat.id)
    if persona and not persona["enabled"]:
        return

    system_prompt = persona["prompt"] if persona else DEFAULT_PROMPT

    await message.chat.send_action("typing")
    response = await ask_ai(user_msg, system_prompt)
    logger.info(f"AI response: {response[:100]}")
    await db.save_chat(message.chat.id, message.from_user.id, user_msg, response)

    audio_path = await text_to_speech(response)
    if audio_path:
        try:
            await message.reply_voice(FSInputFile(audio_path))
            return
        except Exception as e:
            logger.error(f"Voice reply failed: {e}")

    try:
        await message.reply(response)
    except Exception as e:
        logger.error(f"Text reply failed: {e}")
