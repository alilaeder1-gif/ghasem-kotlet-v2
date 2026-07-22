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

_chatbot = None


def get_chatbot():
    global _chatbot
    if _chatbot is not None:
        return _chatbot
    try:
        import hugchat
        from hugchat.login import Login
        hf_email = os.getenv("HF_EMAIL", "")
        hf_pass = os.getenv("HF_PASSWORD", "")
        if hf_email and hf_pass:
            sign = Login(hf_email, hf_pass)
            cookies = sign.login()
            _chatbot = hugchat.ChatBot(cookies=cookies.get_dict())
        else:
            import requests
            cookies = requests.get("https://huggingface.co/chat/").cookies
            _chatbot = hugchat.ChatBot(cookies=cookies.get_dict())
        return _chatbot
    except Exception as e:
        logger.error(f"Chatbot init error: {e}")
        return None


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


def _call_chat(user_message: str, system_prompt: str) -> str:
    chatbot = get_chatbot()
    if not chatbot:
        return "⚠️ خطا: اتصال به HuggingFace Chat برقرار نشد."

    try:
        conversation_id = chatbot.new_conversation(
            model=AI_MODEL,
            system_prompt=system_prompt,
            turn=1
        )
        chatbot.change_conversation(conversation_id)
        response = ""
        for resp in chatbot.chat(user_message):
            if resp:
                if isinstance(resp, dict) and "token" in resp:
                    response += resp["token"]
                elif isinstance(resp, str):
                    response += resp
        try:
            chatbot.delete_conversation(conversation_id)
        except:
            pass
        return response.strip() or "پاسخی دریافت نشد."
    except Exception as e:
        try:
            chatbot.delete_conversation(conversation_id)
        except:
            pass
        return f"⚠️ خطا در اتصال: {str(e)[:200]}"


async def ask_ai(user_message: str, system_prompt: str = None, chat_history: list = None) -> str:
    prompt = system_prompt or DEFAULT_PROMPT
    cached = await cache.get_ai_response(user_message, prompt)
    if cached:
        return cached

    response = await asyncio.to_thread(_call_chat, user_message, prompt)
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
