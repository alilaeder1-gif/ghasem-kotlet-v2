from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command
from database import db
from handlers.permissions import is_group_admin

router = Router()
_warns: dict[str, int] = {}
MAX_WARNS = 3


def _key(chat_id: int, user_id: int) -> str:
    return f"{chat_id}:{user_id}"


@router.message(Command("warn"))
async def warn_user(message: Message):
    if not await is_group_admin(message.bot, message.chat.id, message.from_user.id):
        return await message.reply("❌ فقط ادمین‌های گروه.")
    if not message.reply_to_message:
        return await message.reply("لطفاً روی پیام کاربر ریپلای کن.")
    user = message.reply_to_message.from_user
    reason = message.text.replace("/warn", "").strip() or "بدون دلیل"
    k = _key(message.chat.id, user.id)
    _warns[k] = _warns.get(k, 0) + 1
    count = _warns[k]
    await db.log_admin_action(message.from_user.id, message.chat.id, "warn", user.id, reason)
    if count >= MAX_WARNS:
        try:
            await message.chat.ban(user.id)
            await db.ban_user(message.chat.id, user.id, f"Auto-ban after {MAX_WARNS} warns")
            _warns.pop(k, None)
            await db.log_admin_action(message.from_user.id, message.chat.id, "auto_ban", user.id, f"{MAX_WARNS} warns")
            return await message.reply(f"🚫 {user.full_name} بعد از {MAX_WARNS} اخطار بن شد.")
        except Exception as e:
            return await message.reply(f"❌ خطا در بن خودکار: {e}")
    remain = MAX_WARNS - count
    await message.reply(f"⚠️ {user.full_name} اخطار {count}/{MAX_WARNS}.\nدلیل: {reason}\n{remain} اخطار تا بن.")


@router.message(Command("warns"))
async def check_warns(message: Message):
    if not await is_group_admin(message.bot, message.chat.id, message.from_user.id):
        return await message.reply("❌ فقط ادمین‌های گروه.")
    target = message.reply_to_message.from_user if message.reply_to_message else message.from_user
    k = _key(message.chat.id, target.id)
    count = _warns.get(k, 0)
    await message.reply(f"📋 {target.full_name}: {count} اخطار از {MAX_WARNS}.")


@router.message(Command("delwarn"))
async def del_warn(message: Message):
    if not await is_group_admin(message.bot, message.chat.id, message.from_user.id):
        return await message.reply("❌ فقط ادمین‌های گروه.")
    if not message.reply_to_message:
        return await message.reply("لطفاً روی پیام کاربر ریپلای کن.")
    user = message.reply_to_message.from_user
    k = _key(message.chat.id, user.id)
    if k in _warns and _warns[k] > 0:
        _warns[k] -= 1
        await db.log_admin_action(message.from_user.id, message.chat.id, "delwarn", user.id)
        await message.reply(f"✅ یک اخطار از {user.full_name} کم شد. ({_warns[k]}/{MAX_WARNS})")
    else:
        await message.reply(f"{user.full_name} اخطاری ندارد.")
