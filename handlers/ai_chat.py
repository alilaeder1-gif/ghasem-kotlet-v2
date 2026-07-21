import aiohttp
from aiogram import Router, F
from aiogram.types import Message
from config import HUGGINGFACE_API_KEY, AI_MODEL
from database import db

router = Router()

DEFAULT_PROMPT = (
    "تو یک دستیار هوشمند در گروه تلگرام هستی. "
    "به فارسی پاسخ بده، مختصر و مفید باش. "
    "اگر کسی باهات حرف زد جواب بده. "
    "به سوالات فنی، عمومی و چت دوستانه جواب بده. "
    "پاسخ‌هایت کوتاه و مناسب گروه باشد."
)


async def ask_ai(user_message: str, system_prompt: str = None, chat_history: list = None) -> str:
    if not HUGGINGFACE_API_KEY:
        return "⚠️ کلید API تنظیم نشده. لطفاً HUGGINGFACE_API_KEY رو در فایل .env تنظیم کنید."

    prompt = system_prompt or DEFAULT_PROMPT
    messages = [{"role": "system", "content": prompt}]
    if chat_history:
        messages.extend(chat_history[-6:])
    messages.append({"role": "user", "content": user_message})

    url = f"https://api-inference.huggingface.co/models/{AI_MODEL}"
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
    payload = {"messages": messages, "max_new_tokens": 512, "temperature": 0.7, "return_full_text": False}

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                if resp.status == 200:
                    data = await resp.json()
                    if isinstance(data, list) and data:
                        return data[0].get("generated_text", "پاسخی دریافت نشد.")
                    elif isinstance(data, dict):
                        return data.get("generated_text", "پاسخی دریافت نشد.")
                    return "پاسخی دریافت نشد."
                elif resp.status == 503:
                    return "⏳ مدل در حال بارگذاری است، لطفاً چند لحظه صبر کنید."
                else:
                    return f"⚠️ خطا: {resp.status}"
    except Exception as e:
        return f"⚠️ خطا در اتصال: {str(e)[:100]}"


@router.message(F.text & ~F.text.startswith("/"))
async def ai_chat_handler(message: Message):
    if not message.chat.type in ("group", "supergroup"):
        return

    bot_info = await message.bot.get_me()
    bot_username = bot_info.username

    text = message.text or ""
    is_mention = bot_username and f"@{bot_username}" in text
    is_reply = (
        message.reply_to_message
        and message.reply_to_message.from_user
        and message.reply_to_message.from_user.id == bot_info.id
    )

    if not is_mention and not is_reply:
        return

    if is_mention:
        user_msg = text.replace(f"@{bot_username}", "").strip()
    else:
        user_msg = text.strip()

    if not user_msg:
        user_msg = "سلام"

    persona = await db.get_persona(message.chat.id)
    if persona and not persona["enabled"]:
        return

    system_prompt = persona["prompt"] if persona else DEFAULT_PROMPT

    await message.chat.send_action("typing")
    response = await ask_ai(user_msg, system_prompt)
    await db.save_chat(message.chat.id, message.from_user.id, user_msg, response)

    try:
        await message.reply(response)
    except Exception:
        pass
