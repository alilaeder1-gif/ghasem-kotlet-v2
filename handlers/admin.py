from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from config import ADMIN_IDS
import re

router = Router()

PERSIAN_RE = re.compile(r"^(بن|سیک|سیکتیر|میوت|آنبن|انبن|آنمیوت|پین|نگ)(?:\s|$)")


# ─── Persian text commands (بدون / ) ───

PERSIAN_CMDS = {
    "بن": "ban", "سیک": "kick", "سیکتیر": "kickban",
    "میوت": "mute", "آنبن": "unban", "انبن": "unban",
    "آنمیوت": "unmute", "پین": "pin", "نگ": "tag",
}


@router.message(F.text.regexp(PERSIAN_RE), F.chat.type.in_({"group", "supergroup"}))
async def persian_cmd_handler(message: Message):
    text = message.text.strip()
    first = text.split()[0]
    cmd = PERSIAN_CMDS.get(first)
    if not cmd:
        return

    chat_member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    if chat_member.status not in ("creator", "administrator"):
        return await message.reply("❌ فقط ادمین‌ها می‌تونن از این دستور استفاده کنن.")

    user = message.reply_to_message.from_user if message.reply_to_message else None

    if cmd == "tag":
        return await _cmd_tag(message, text, first)

    if not user:
        return await message.reply("❌ روی پیام کاربر ریپلای کن.")
    if user.id in ADMIN_IDS:
        return await message.reply("❌ نمی‌تونم روی ادمین‌ها اعمال کنم.")

    args = text[len(first):].strip()
    reason = args or "بدون دلیل"

    if cmd == "ban":
        try:
            await message.chat.ban(user.id)
            from database import db
            await db.ban_user(message.chat.id, user.id, reason)
            await message.reply(f"🚫 {user.full_name} بن شد.\nدلیل: {reason}")
        except Exception as e:
            await message.reply(f"❌ خطا: {e}")

    elif cmd == "kick":
        try:
            await message.chat.ban(user.id)
            await message.chat.unban(user.id)
            await message.reply(f"👢 {user.full_name} کیک شد.\nدلیل: {reason}")
        except Exception as e:
            await message.reply(f"❌ خطا: {e}")

    elif cmd == "kickban":
        try:
            await message.chat.ban(user.id)
            from database import db
            await db.ban_user(message.chat.id, user.id, reason)
            await message.reply(f"🚫👢 {user.full_name} کیک و بن شد.\nدلیل: {reason}")
        except Exception as e:
            await message.reply(f"❌ خطا: {e}")

    elif cmd == "mute":
        from utils.helpers import parse_duration
        parts = args.split(None, 1)
        duration = parse_duration(parts[0]) if parts else 0
        mute_reason = parts[1] if len(parts) > 1 else "بدون دلیل"
        try:
            permissions = message.chat.permissions.model_copy()
            permissions.can_send_messages = False
            await message.chat.restrict(user.id, permissions)
            from database import db
            await db.mute_user(message.chat.id, user.id, duration, mute_reason)
            dur_text = format_duration(duration) if duration else "نامحدود"
            await message.reply(f"🔇 {user.full_name} میوت شد.\nمدت: {dur_text}\nدلیل: {mute_reason}")
        except Exception as e:
            await message.reply(f"❌ خطا: {e}")

    elif cmd == "unban":
        try:
            await message.chat.unban(user.id)
            from database import db
            await db.unban_user(message.chat.id, user.id)
            await message.reply(f"✅ {user.full_name} آنب بن شد.")
        except Exception as e:
            await message.reply(f"❌ خطا: {e}")

    elif cmd == "unmute":
        try:
            permissions = message.chat.permissions
            await message.chat.restrict(user.id, permissions)
            from database import db
            await db.unmute_user(message.chat.id, user.id)
            await message.reply(f"🔊 {user.full_name} آنمیوت شد.")
        except Exception as e:
            await message.reply(f"❌ خطا: {e}")

    elif cmd == "pin":
        try:
            await message.reply_to_message.pin()
            await message.reply("📌 پیام پین شد.")
        except Exception as e:
            await message.reply(f"❌ خطا: {e}")


async def _cmd_tag(message: Message, text: str, first: str):
    tag_text = text[len(first):].strip()
    users = await db.get_group_users(message.chat.id)
    if not users:
        return await message.reply("❌ هیچ کاربری نیست.")
    mentions = []
    for u in users[:30]:
        name = u["full_name"] or u["username"] or f"user{u['user_id']}"
        mentions.append(f"[{name}](tg://user?id={u['user_id']})")
    chunk_size = 5
    for i in range(0, len(mentions), chunk_size):
        chunk = mentions[i:i + chunk_size]
        msg = " ".join(chunk)
        if tag_text:
            msg = f"{tag_text}\n\n{msg}"
        await message.reply(msg)
        import asyncio
        await asyncio.sleep(1)


# ─── Command-based handlers (با / ) ───

@router.message(Command("ban"))
async def ban_user(message: Message):
    if not message.reply_to_message:
        return await message.reply("لطفاً روی پیام کاربر مورد نظر ریپلای کنید.")
    user = message.reply_to_message.from_user
    chat_member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    if chat_member.status not in ("creator", "administrator"):
        return await message.reply("فقط ادمین‌ها می‌تونن بن کنن.")
    if user.id in ADMIN_IDS:
        return await message.reply("نمی‌توانید ادمین‌ها رو بن کنید.")
    reason = message.text.replace("/ban", "").strip() or "بدون دلیل"
    try:
        await message.chat.ban(user.id)
        from database import db
        await db.ban_user(message.chat.id, user.id, reason)
        await message.reply(f"کاربر {user.full_name} بن شد.\nدلیل: {reason}")
    except Exception as e:
        await message.reply(f"خطا در بن کردن: {e}")


@router.message(Command("unban"))
async def unban_user(message: Message):
    if not message.reply_to_message:
        return await message.reply("لطفاً روی پیام کاربر مورد نظر ریپلای کنید.")
    user = message.reply_to_message.from_user
    chat_member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    if chat_member.status not in ("creator", "administrator"):
        return await message.reply("فقط ادمین‌ها می‌تونن آنب بن کنن.")
    try:
        await message.chat.unban(user.id)
        from database import db
        await db.unban_user(message.chat.id, user.id)
        await message.reply(f"کاربر {user.full_name} آنب بن شد.")
    except Exception as e:
        await message.reply(f"خطا در آنب بن کردن: {e}")


@router.message(Command("kick"))
async def kick_user(message: Message):
    if not message.reply_to_message:
        return await message.reply("لطفاً روی پیام کاربر مورد نظر ریپلای کنید.")
    user = message.reply_to_message.from_user
    chat_member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    if chat_member.status not in ("creator", "administrator"):
        return await message.reply("فقط ادمین‌ها می‌تونن کیک کنن.")
    if user.id in ADMIN_IDS:
        return await message.reply("نمی‌توانید ادمین‌ها رو کیک کنید.")
    try:
        await message.chat.ban(user.id)
        await message.chat.unban(user.id)
        await message.reply(f"کاربر {user.full_name} کیک شد.")
    except Exception as e:
        await message.reply(f"خطا در کیک کردن: {e}")


@router.message(Command("mute"))
async def mute_user(message: Message):
    if not message.reply_to_message:
        return await message.reply("لطفاً روی پیام کاربر مورد نظر ریپلای کنید.")
    user = message.reply_to_message.from_user
    chat_member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    if chat_member.status not in ("creator", "administrator"):
        return await message.reply("فقط ادمین‌ها می‌تونن میوت کنن.")
    if user.id in ADMIN_IDS:
        return await message.reply("نمی‌توانید ادمین‌ها رو میوت کنید.")
    from utils.helpers import parse_duration
    args = message.text.replace("/mute", "").strip().split(None, 1)
    duration = parse_duration(args[0]) if args else 0
    reason = args[1] if len(args) > 1 else "بدون دلیل"
    try:
        permissions = message.chat.permissions.model_copy()
        permissions.can_send_messages = False
        await message.chat.restrict(user.id, permissions)
        from database import db
        await db.mute_user(message.chat.id, user.id, duration, reason)
        dur_text = format_duration(duration) if duration else "نامحدود"
        await message.reply(f"کاربر {user.full_name} میوت شد.\nمدت: {dur_text}\nدلیل: {reason}")
    except Exception as e:
        await message.reply(f"خطا در میوت کردن: {e}")


@router.message(Command("unmute"))
async def unmute_user(message: Message):
    if not message.reply_to_message:
        return await message.reply("لطفاً روی پیام کاربر مورد نظر ریپلای کنید.")
    user = message.reply_to_message.from_user
    chat_member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    if chat_member.status not in ("creator", "administrator"):
        return await message.reply("فقط ادمین‌ها می‌تونن آنمیوت کنن.")
    try:
        permissions = message.chat.permissions
        await message.chat.restrict(user.id, permissions)
        from database import db
        await db.unmute_user(message.chat.id, user.id)
        await message.reply(f"کاربر {user.full_name} آنمیوت شد.")
    except Exception as e:
        await message.reply(f"خطا در آنمیوت کردن: {e}")


@router.message(Command("pin"))
async def pin_message(message: Message):
    if not message.reply_to_message:
        return await message.reply("لطفاً روی پیام مورد نظر ریپلای کنید.")
    chat_member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    if chat_member.status not in ("creator", "administrator"):
        return await message.reply("فقط ادمین‌ها می‌تونن پین کنن.")
    try:
        await message.reply_to_message.pin()
        await message.reply("پیام پین شد.")
    except Exception as e:
        await message.reply(f"خطا در پین کردن: {e}")


def format_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds} ثانیه"
    elif seconds < 3600:
        return f"{seconds // 60} دقیقه"
    elif seconds < 86400:
        return f"{seconds // 3600} ساعت"
    else:
        return f"{seconds // 86400} روز"
