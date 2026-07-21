import re
from aiogram import Router, F
from aiogram.types import Message
from database import db
from config import SPAM_THRESHOLD, SPAM_WINDOW

router = Router()

SPAM_PATTERNS = [
    r"(bit\.ly|tinyurl\.com|t\.me/\+)",
    r"(پیام\s*میدم| DM\s*me| پیام\s*بده)",
    r"(تخفیف\s*ویژه|عرضه\s*انحصاری|رایگان\s*بگیر)",
    r"( join\s*now|کلیک\s*کن|ورود\s*به\s*گروه)",
]


async def is_spam(text: str) -> bool:
    if not text:
        return False
    for pattern in SPAM_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True
    return False


@router.message(F.text)
async def check_spam(message: Message):
    if not message.text or not message.chat.type in ("group", "supergroup"):
        return

    chat_member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    if chat_member.status in ("creator", "administrator"):
        return

    muted = await db.is_muted(message.chat.id, message.from_user.id)
    if muted:
        try:
            await message.delete()
        except Exception:
            pass
        return

    if await is_spam(message.text):
        try:
            await message.delete()
            await db.log_spam(message.chat.id, message.from_user.id, message.text[:100])
            count = await db.get_spam_count(message.chat.id, message.from_user.id, SPAM_WINDOW)
            if count >= SPAM_THRESHOLD:
                try:
                    await message.chat.ban(message.from_user.id)
                    await message.reply(f"کاربر {message.from_user.full_name} به دلیل اسپم بن شد.")
                except Exception:
                    pass
            else:
                await message.reply(
                    f"{message.from_user.full_name} پیام شما حذف شد (تشخیص اسپم).\n"
                    f"اخطار: {count}/{SPAM_THRESHOLD}",
                    delete_after=5
                )
        except Exception:
            pass
