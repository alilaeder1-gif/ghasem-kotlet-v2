import re
import asyncio
from collections import defaultdict
from datetime import datetime, timedelta
from aiogram import Router, F
from aiogram.types import Message, ChatMemberUpdated
from aiogram.filters import Command
from aiogram.enums import ChatType
from database import db
from config import SPAM_THRESHOLD, SPAM_WINDOW

router = Router()

SPAM_PATTERNS = [
    r"(bit\.ly|tinyurl\.com|t\.me/\+|t\.me/joinchat)",
    r"(پیام\s*میدم| DM\s*me| پیام\s*بده|پیام\s*خصوصی)",
    r"(تخفیف\s*ویژه|عرضه\s*انحصاری|رایگان\s*بگیر|فروش\s*فوری)",
    r"( join\s*now|کلیک\s*کن|ورود\s*به\s*گروه|عضویت\s*کن)",
    r"(پشتیبانی\s*فوری|واریز\s*کن|شارژ\s*کن|برداشت\s*کن)",
    r"(سود\s*روزانه|سرمایه‌گذاری\s*با\s*سود|درآمد\s*میلیونی|کسب\s*درآمد)",
    r"(ارز\s*دیجیتال|کریپتو|bitcoin|usdt|تتر|بیت‌کوین\s*رایگان)",
    r"(sig|sign|سایت\s*شرط‌بندی|شرط\s*بندی|پیشبینی\s*فوتبال)",
    r"(سکسی|دختر\s*خوشگل|حرف\s*حساس|چت\s*خصوصی|سایت\s*دوستی)",
    r"(bot\s*father|ساخت\s*ربات|ساخت\s*بات|ساخت\s*ربات\s*تلگرام)",
    r"(shart\s*bandi|shartbandi|پیشبینی\s*فوتبال|khaneye\s*shart)",
    r"(sood\s*roozane|sarmaye\s*gozari|daramad\s*melioni|kar\s*dar\s*khone)",
    r"(free\s*bitcoin|bitcoin\s*free|earning|earn\s*money|work\s*from\s*home)",
    r"(usdt\s*free|busd|سود\s*usdt|تتر\s*رایگان|تتر\s*هدیه)",
]

FLOOD_LIMIT = 5
FLOOD_WINDOW = 3
NEW_USER_LINK_RESTRICT = timedelta(minutes=30)
SPAM_SCORE_BAN = 10

user_msg_times = defaultdict(list)
user_spam_score = defaultdict(int)
recent_messages = defaultdict(list)


def is_spam(text: str) -> tuple:
    if not text:
        return False, ""
    for pattern in SPAM_PATTERNS:
        if re.search(pattern, text, re.IGNORECASE):
            return True, pattern
    return False, ""


def is_flood(user_id: int, chat_id: int) -> bool:
    key = f"{user_id}:{chat_id}"
    now = datetime.now()
    user_msg_times[key] = [t for t in user_msg_times[key] if now - t < timedelta(seconds=FLOOD_WINDOW)]
    user_msg_times[key].append(now)
    return len(user_msg_times[key]) > FLOOD_LIMIT


def is_repeated(user_id: int, chat_id: int, text: str) -> bool:
    key = f"{user_id}:{chat_id}:repeat"
    recent_messages[key].append((text, datetime.now()))
    recent_messages[key] = [(t, dt) for t, dt in recent_messages[key] if datetime.now() - dt < timedelta(seconds=30)]
    similar = sum(1 for t, _ in recent_messages[key] if t == text)
    return similar >= 3


async def is_new_user_spam(message: Message) -> bool:
    try:
        chat_member = await message.chat.get_member(message.from_user.id)
        if chat_member.status in ("creator", "administrator", "member"):
            if chat_member.status == "member":
                now = datetime.now()
                joined_at = chat_member.joined_date or chat_member.user.joined_date
                if joined_at:
                    if isinstance(joined_at, (int, float)):
                        joined_at = datetime.fromtimestamp(joined_at)
                    if now - joined_at < NEW_USER_LINK_RESTRICT:
                        return "link" in (message.text or "").lower() or bool(re.search(r"t\.me|http|www\.", message.text or ""))
    except Exception:
        pass
    return False


def score_text(text: str) -> int:
    score = 0
    emoji_count = len(re.findall(r"[😀-🙏🌀-🗿🚀-🛸]", text))
    caps_count = sum(1 for c in text if c.isupper())
    repeat_char = re.search(r"(.)\1{4,}", text)
    all_caps = caps_count > len(text) * 0.7 and len(text) > 20

    if emoji_count > 5:
        score += 2
    if repeat_char:
        score += 2
    if all_caps:
        score += 3
    if len(text) > 500:
        score += 1
    return score


LINK_RE = re.compile(r"(https?://[^\s]+|t\.me/[a-zA-Z0-9_]+|www\.[^\s]+)")


async def check_link_delete(message: Message, settings: dict) -> bool:
    if not settings.get("link_delete_enabled"):
        return True
    delay = settings.get("link_delete_delay", 0)
    text = message.text or message.caption or ""
    if not LINK_RE.search(text):
        return True
    if delay == 0:
        return False
    try:
        chat_member = await message.chat.get_member(message.from_user.id)
        if chat_member.status == "member":
            now = datetime.now()
            joined_at = chat_member.joined_date
            if joined_at:
                if isinstance(joined_at, (int, float)):
                    joined_at = datetime.fromtimestamp(joined_at)
                minutes_since_join = (now - joined_at).total_seconds() / 60
                if minutes_since_join < delay:
                    return False
    except Exception:
        pass
    return True


async def take_action(chat_id: int, user_id: int, full_name: str, bot, reason: str):
    user_spam_score[user_id] += 1
    score = user_spam_score[user_id]

    if score >= SPAM_SCORE_BAN:
        try:
            await bot.ban_chat_member(chat_id, user_id)
            await bot.send_message(chat_id, f"🚫 کاربر {full_name} به دلیل اسپم مکرر بن شد.")
            user_spam_score[user_id] = 0
        except Exception:
            pass
    elif score >= SPAM_SCORE_BAN // 2:
        try:
            await bot.restrict_chat_member(
                chat_id, user_id,
                permissions={"can_send_messages": False}
            )
            await asyncio.sleep(3600)
            try:
                await bot.restrict_chat_member(
                    chat_id, user_id,
                    permissions={"can_send_messages": True}
                )
            except Exception:
                pass
        except Exception:
            pass
    else:
        try:
            await bot.send_message(
                chat_id,
                f"⚠️ {full_name} اسپم تشخیص داده شد.\n"
                f"اخطار: {score}/{SPAM_SCORE_BAN} → بن دائمی"
            )
        except Exception:
            pass


@router.message(F.text)
async def check_spam(message: Message):
    if not message.text or message.chat.type not in ("group", "supergroup"):
        return

    chat_member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    if chat_member.status in ("creator", "administrator"):
        return

    settings = await db.get_group_settings(message.chat.id)
    if not settings.get("spam_protection", True):
        return

    muted = await db.is_muted(message.chat.id, message.from_user.id)
    if muted:
        try:
            await message.delete()
        except Exception:
            pass
        return

    if not await check_link_delete(message, settings):
        try:
            await message.delete()
            await db.log_spam(message.chat.id, message.from_user.id, "[link] " + (message.text or "")[:100])
        except Exception:
            pass
        return

    text = message.text

    spam_detected, matched = is_spam(text)
    if spam_detected:
        try:
            await message.delete()
            await db.log_spam(message.chat.id, message.from_user.id, text[:100])
            await take_action(message.chat.id, message.from_user.id, message.from_user.full_name, message.bot, matched)
            return
        except Exception:
            pass

    if settings.get("flood_protection", True) and is_flood(message.from_user.id, message.chat.id):
        try:
            await message.delete()
            await db.log_spam(message.chat.id, message.from_user.id, "[flood] " + text[:100])
            await take_action(message.chat.id, message.from_user.id, message.from_user.full_name, message.bot, "flood")
        except Exception:
            pass
        return

    if is_repeated(message.from_user.id, message.chat.id, text):
        try:
            await message.delete()
            await db.log_spam(message.chat.id, message.from_user.id, "[repeat] " + text[:100])
        except Exception:
            pass
        return

    if await is_new_user_spam(message):
        try:
            await message.delete()
            await db.log_spam(message.chat.id, message.from_user.id, "[new_user_link] " + text[:100])
            await message.bot.send_message(
                message.chat.id,
                f"🔒 {message.from_user.full_name} کاربران جدید تا ۳۰ دقیقه نمی‌تونن لینک بفرستن."
            )
        except Exception:
            pass
        return

    text_score = score_text(text)
    if text_score >= 3:
        try:
            await message.delete()
            await db.log_spam(message.chat.id, message.from_user.id, "[score] " + text[:100])
            await message.bot.send_message(
                message.chat.id,
                f"⚠️ {message.from_user.full_name} پیام شما به دلیل محتوای نامناسب حذف شد."
            )
        except Exception:
            pass
        return


@router.message(F.new_chat_members)
async def new_member_anti_spam(message: Message):
    for member in message.new_chat_members:
        if member.is_bot:
            continue
        if message.chat.type not in ("group", "supergroup"):
            continue
        chat_id = message.chat.id
        user_id = member.id
        msg = await message.answer(
            f"👋 {member.full_name} خوش اومدی!\n"
            f"🔒 تا ۳۰ دقیقه حق ارسال لینک نداری.",
            delete_after=10
        )


@router.message(Command("linkdelete"))
async def set_link_delete(message: Message):
    if message.chat.type not in ("group", "supergroup"):
        return
    chat_member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    if chat_member.status not in ("creator", "administrator"):
        return await message.reply("فقط ادمین‌ها می‌تونن تنظیم کنن.")

    args = message.text.replace("/linkdelete", "").strip().split()
    if len(args) < 1:
        return await message.reply(
            "🔗 **مدیریت حذف لینک**\n\n"
            "/linkdelete on - حذف فوری تمام لینک‌ها\n"
            "/linkdelete 30 - حذف لینک تا ۳۰ دقیقه بعد از جوین\n"
            "/linkdelete off - غیرفعال کردن\n\n"
            "عدد به معنی دقیقه هست (۰ = فوری)."
        )

    if args[0].lower() == "off":
        await db.update_group_settings(message.chat.id, link_delete_enabled=0, link_delete_delay=0)
        return await message.reply("❌ حذف خودکار لینک غیرفعال شد.")

    if args[0].lower() == "on" or args[0] == "0":
        await db.update_group_settings(message.chat.id, link_delete_enabled=1, link_delete_delay=0)
        return await message.reply("✅ حذف فوری لینک فعال شد. همه لینک‌ها حذف میشن.")

    try:
        delay = int(args[0])
        if delay < 1:
            delay = 1
        await db.update_group_settings(message.chat.id, link_delete_enabled=1, link_delete_delay=delay)
        await message.reply(f"✅ حذف لینک فعال شد. لینک کاربران جدید تا {delay} دقیقه حذف میشه.")
    except ValueError:
        await message.reply("عدد معتبر وارد کن.")
