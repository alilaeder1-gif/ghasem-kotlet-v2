from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from database import db
from utils.helpers import parse_duration
from handlers.permissions import is_group_admin

router = Router()
_PERSIAN_MUTE = r"^(میوت|آنمیوت|آنمیت)(?:\s|$)"


def format_duration(seconds: int) -> str:
    if seconds < 60:
        return f"{seconds} ثانیه"
    if seconds < 3600:
        return f"{seconds // 60} دقیقه"
    if seconds < 86400:
        return f"{seconds // 3600} ساعت"
    return f"{seconds // 86400} روز"


@router.message(Command("mute"))
async def mute_user(message: Message):
    if not await is_group_admin(message.bot, message.chat.id, message.from_user.id):
        return await message.reply("❌ فقط ادمین‌های گروه.")
    if not message.reply_to_message:
        return await message.reply("لطفاً روی پیام کاربر ریپلای کن.")
    user = message.reply_to_message.from_user
    args = message.text.replace("/mute", "").strip().split(None, 1)
    duration = parse_duration(args[0]) if args else 0
    reason = args[1] if len(args) > 1 else "بدون دلیل"
    try:
        permissions = message.chat.permissions.model_copy()
        permissions.can_send_messages = False
        await message.chat.restrict(user.id, permissions)
        await db.mute_user(message.chat.id, user.id, duration, reason)
        await db.log_admin_action(message.from_user.id, message.chat.id, "mute", user.id, reason)
        dur_text = format_duration(duration) if duration else "نامحدود"
        await message.reply(f"🔇 {user.full_name} میوت شد.\nمدت: {dur_text}\nدلیل: {reason}")
    except Exception as e:
        await message.reply(f"❌ خطا: {e}")


@router.message(Command("unmute"))
async def unmute_user(message: Message):
    if not await is_group_admin(message.bot, message.chat.id, message.from_user.id):
        return await message.reply("❌ فقط ادمین‌های گروه.")
    if not message.reply_to_message:
        return await message.reply("لطفاً روی پیام کاربر ریپلای کن.")
    user = message.reply_to_message.from_user
    try:
        await message.chat.restrict(user.id, message.chat.permissions)
        await db.unmute_user(message.chat.id, user.id)
        await db.log_admin_action(message.from_user.id, message.chat.id, "unmute", user.id)
        await message.reply(f"🔊 {user.full_name} آنمیوت شد.")
    except Exception as e:
        await message.reply(f"❌ خطا: {e}")


@router.message(F.text.regexp(_PERSIAN_MUTE), F.chat.type.in_({"group", "supergroup"}))
async def persian_mute_handler(message: Message):
    text = message.text.strip()
    first = text.split()[0]
    cmds = {"میوت": "mute", "آنمیوت": "unmute", "آنمیت": "unmute"}
    cmd = cmds.get(first)
    if not cmd:
        return

    if not await is_group_admin(message.bot, message.chat.id, message.from_user.id):
        return await message.reply("❌ فقط ادمین‌های گروه.")
    if not message.reply_to_message:
        return await message.reply("❌ روی پیام ریپلای کن.")
    user = message.reply_to_message.from_user

    try:
        if cmd == "mute":
            args = text[len(first):].strip()
            parts = args.split(None, 1)
            duration = parse_duration(parts[0]) if parts else 0
            reason = parts[1] if len(parts) > 1 else "بدون دلیل"
            permissions = message.chat.permissions.model_copy()
            permissions.can_send_messages = False
            await message.chat.restrict(user.id, permissions)
            await db.mute_user(message.chat.id, user.id, duration, reason)
            await db.log_admin_action(message.from_user.id, message.chat.id, "mute", user.id, reason)
            dur_text = format_duration(duration) if duration else "نامحدود"
            await message.reply(f"🔇 {user.full_name} میوت شد.\nمدت: {dur_text}\nدلیل: {reason}")
        elif cmd == "unmute":
            await message.chat.restrict(user.id, message.chat.permissions)
            await db.unmute_user(message.chat.id, user.id)
            await db.log_admin_action(message.from_user.id, message.chat.id, "unmute", user.id)
            await message.reply(f"🔊 {user.full_name} آنمیوت شد.")
    except Exception as e:
        await message.reply(f"❌ خطا: {e}")
