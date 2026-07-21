from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from config import ADMIN_IDS

router = Router()


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
