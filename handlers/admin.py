from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from handlers.permissions import is_group_admin
import re

router = Router()

PERSIAN_RE = re.compile(r"^(بن|سیک|سیکتیر|میوت|آنبن|انبن|آنمیوت|پین|نگ|منشن)(?:\s|$)")

PERSIAN_CMDS = {
    "بن": "ban", "سیک": "kick", "سیکتیر": "kickban",
    "میوت": "mute", "آنبن": "unban", "انبن": "unban",
    "آنمیوت": "unmute", "پین": "pin", "نگ": "tag", "منشن": "tag",
}


# ─── Helper ───

async def _assert_group_admin(message: Message):
    if not await is_group_admin(message.bot, message.chat.id, message.from_user.id):
        await message.reply("❌ فقط ادمین‌های گروه می‌تونن از این دستور استفاده کنن.")
        return False
    return True


# ─── Persian text commands ───

@router.message(F.text.regexp(PERSIAN_RE), F.chat.type.in_({"group", "supergroup"}))
async def persian_cmd_handler(message: Message):
    if not await _assert_group_admin(message):
        return

    text = message.text.strip()
    first = text.split()[0]
    cmd = PERSIAN_CMDS.get(first)

    user = message.reply_to_message.from_user if message.reply_to_message else None

    if cmd == "tag":
        return await _cmd_tag(message, text, first)
    if not user:
        return await message.reply("❌ روی پیام کاربر ریپلای کن.")

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
    from database import db
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


# ─── Command-based handlers ───

@router.message(Command("ban"))
async def ban_user(message: Message):
    if not await _assert_group_admin(message):
        return
    if not message.reply_to_message:
        return await message.reply("لطفاً روی پیام کاربر مورد نظر ریپلای کنید.")
    user = message.reply_to_message.from_user
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
    if not await _assert_group_admin(message):
        return
    if not message.reply_to_message:
        return await message.reply("لطفاً روی پیام کاربر مورد نظر ریپلای کنید.")
    user = message.reply_to_message.from_user
    try:
        await message.chat.unban(user.id)
        from database import db
        await db.unban_user(message.chat.id, user.id)
        await message.reply(f"کاربر {user.full_name} آنب بن شد.")
    except Exception as e:
        await message.reply(f"خطا در آنب بن کردن: {e}")


@router.message(Command("kick"))
async def kick_user(message: Message):
    if not await _assert_group_admin(message):
        return
    if not message.reply_to_message:
        return await message.reply("لطفاً روی پیام کاربر مورد نظر ریپلای کنید.")
    user = message.reply_to_message.from_user
    try:
        await message.chat.ban(user.id)
        await message.chat.unban(user.id)
        await message.reply(f"کاربر {user.full_name} کیک شد.")
    except Exception as e:
        await message.reply(f"خطا در کیک کردن: {e}")


@router.message(Command("mute"))
async def mute_user(message: Message):
    if not await _assert_group_admin(message):
        return
    if not message.reply_to_message:
        return await message.reply("لطفاً روی پیام کاربر مورد نظر ریپلای کنید.")
    user = message.reply_to_message.from_user
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
    if not await _assert_group_admin(message):
        return
    if not message.reply_to_message:
        return await message.reply("لطفاً روی پیام کاربر مورد نظر ریپلای کنید.")
    user = message.reply_to_message.from_user
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
    if not await _assert_group_admin(message):
        return
    if not message.reply_to_message:
        return await message.reply("لطفاً روی پیام مورد نظر ریپلای کنید.")
    try:
        await message.reply_to_message.pin()
        await message.reply("پیام پین شد.")
    except Exception as e:
        await message.reply(f"خطا در پین کردن: {e}")


@router.message(Command("tag"))
async def cmd_tag(message: Message):
    if not await _assert_group_admin(message):
        return
    tag_text = message.text.replace("/tag", "").strip()
    from database import db as _db
    users = await _db.get_group_users(message.chat.id)
    if not users:
        return await message.reply("❌ هیچ کاربری نیست.")
    mentions = []
    for u in users[:30]:
        name = u["full_name"] or u["username"] or f"user{u['user_id']}"
        mentions.append(f"[{name}](tg://user?id={u['user_id']})")
    chunk_size = 5
    import asyncio
    for i in range(0, len(mentions), chunk_size):
        chunk = mentions[i:i + chunk_size]
        msg = " ".join(chunk)
        if tag_text:
            msg = f"{tag_text}\n\n{msg}"
        await message.reply(msg)
        await asyncio.sleep(1)


# ─── Warn system ───

_warns: dict[str, int] = {}
_MAX_WARNS = 3


def _warn_key(chat_id: int, user_id: int) -> str:
    return f"{chat_id}:{user_id}"


@router.message(Command("warn"))
async def warn_user(message: Message):
    if not await _assert_group_admin(message):
        return
    if not message.reply_to_message:
        return await message.reply("لطفاً روی پیام کاربر ریپلای کن.")
    user = message.reply_to_message.from_user
    reason = message.text.replace("/warn", "").strip() or "بدون دلیل"
    k = _warn_key(message.chat.id, user.id)
    _warns[k] = _warns.get(k, 0) + 1
    count = _warns[k]
    try:
        from database import db
        await db.log_admin_action(message.from_user.id, message.chat.id, "warn", user.id, reason)
    except Exception:
        pass
    if count >= _MAX_WARNS:
        try:
            await message.chat.ban(user.id)
            from database import db
            await db.ban_user(message.chat.id, user.id, f"Auto-ban after {_MAX_WARNS} warns")
        except Exception:
            pass
        _warns.pop(k, None)
        return await message.reply(f"🚫 {user.full_name} بعد از {_MAX_WARNS} اخطار بن شد.")
    remain = _MAX_WARNS - count
    await message.reply(f"⚠️ {user.full_name} اخطار {count}/{_MAX_WARNS}.\nدلیل: {reason}\n{remain} اخطار تا بن.")


@router.message(Command("warns"))
async def check_warns(message: Message):
    if not await _assert_group_admin(message):
        return
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    k = _warn_key(message.chat.id, target.id)
    count = _warns.get(k, 0)
    await message.reply(f"📋 {target.full_name}: {count} اخطار از {_MAX_WARNS}.")


@router.message(Command("delwarn"))
async def del_warn(message: Message):
    if not await _assert_group_admin(message):
        return
    if not message.reply_to_message:
        return await message.reply("لطفاً روی پیام کاربر ریپلای کن.")
    user = message.reply_to_message.from_user
    k = _warn_key(message.chat.id, user.id)
    if k in _warns and _warns[k] > 0:
        _warns[k] -= 1
        try:
            from database import db
            await db.log_admin_action(message.from_user.id, message.chat.id, "delwarn", user.id)
        except Exception:
            pass
        await message.reply(f"✅ یک اخطار از {user.full_name} کم شد. ({_warns[k]}/{_MAX_WARNS})")
    else:
        await message.reply(f"{user.full_name} اخطاری ندارد.")


def format_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds} ثانیه"
    elif seconds < 3600:
        return f"{seconds // 60} دقیقه"
    elif seconds < 86400:
        return f"{seconds // 3600} ساعت"
    else:
        return f"{seconds // 86400} روز"
