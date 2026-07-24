from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from database import db
from handlers.permissions import is_group_admin

router = Router()
_PERSIAN_BAN = r"^(بن|انبن|آنبن|سیک|سیکتیر)(?:\s|$)"


@router.message(Command("ban"))
async def ban_user(message: Message):
    if not await is_group_admin(message.bot, message.chat.id, message.from_user.id):
        return await message.reply("❌ فقط ادمین‌های گروه.")
    if not message.reply_to_message:
        return await message.reply("لطفاً روی پیام کاربر ریپلای کن.")
    user = message.reply_to_message.from_user
    reason = message.text.replace("/ban", "").strip() or "بدون دلیل"
    try:
        await message.chat.ban(user.id)
        await db.ban_user(message.chat.id, user.id, reason)
        await db.log_admin_action(message.from_user.id, message.chat.id, "ban", user.id, reason)
        await message.reply(f"🚫 {user.full_name} بن شد.\nدلیل: {reason}")
    except Exception as e:
        await message.reply(f"❌ خطا: {e}")


@router.message(Command("unban"))
async def unban_user(message: Message):
    if not await is_group_admin(message.bot, message.chat.id, message.from_user.id):
        return await message.reply("❌ فقط ادمین‌های گروه.")
    if not message.reply_to_message:
        return await message.reply("لطفاً روی پیام کاربر ریپلای کن.")
    user = message.reply_to_message.from_user
    try:
        await message.chat.unban(user.id)
        await db.unban_user(message.chat.id, user.id)
        await db.log_admin_action(message.from_user.id, message.chat.id, "unban", user.id)
        await message.reply(f"✅ {user.full_name} آنبن شد.")
    except Exception as e:
        await message.reply(f"❌ خطا: {e}")


@router.message(Command("kick"))
async def kick_user(message: Message):
    if not await is_group_admin(message.bot, message.chat.id, message.from_user.id):
        return await message.reply("❌ فقط ادمین‌های گروه.")
    if not message.reply_to_message:
        return await message.reply("لطفاً روی پیام کاربر ریپلای کن.")
    user = message.reply_to_message.from_user
    try:
        await message.chat.ban(user.id)
        await message.chat.unban(user.id)
        await db.log_admin_action(message.from_user.id, message.chat.id, "kick", user.id)
        await message.reply(f"👢 {user.full_name} کیک شد.")
    except Exception as e:
        await message.reply(f"❌ خطا: {e}")


@router.message(F.text.regexp(_PERSIAN_BAN), F.chat.type.in_({"group", "supergroup"}))
async def persian_ban_handler(message: Message):
    text = message.text.strip()
    first = text.split()[0]
    cmds = {"بن": "ban", "انبن": "unban", "آنبن": "unban", "سیک": "kick", "سیکتیر": "kickban"}
    cmd = cmds.get(first)
    if not cmd:
        return

    if not await is_group_admin(message.bot, message.chat.id, message.from_user.id):
        return await message.reply("❌ فقط ادمین‌های گروه.")
    if not message.reply_to_message:
        return await message.reply("❌ روی پیام ریپلای کن.")
    user = message.reply_to_message.from_user

    args = text[len(first):].strip()
    reason = args or "بدون دلیل"

    try:
        if cmd == "ban":
            await message.chat.ban(user.id)
            await db.ban_user(message.chat.id, user.id, reason)
            await db.log_admin_action(message.from_user.id, message.chat.id, "ban", user.id, reason)
            await message.reply(f"🚫 {user.full_name} بن شد.\nدلیل: {reason}")
        elif cmd == "unban":
            await message.chat.unban(user.id)
            await db.unban_user(message.chat.id, user.id)
            await db.log_admin_action(message.from_user.id, message.chat.id, "unban", user.id)
            await message.reply(f"✅ {user.full_name} آنبن شد.")
        elif cmd in ("kick", "kickban"):
            await message.chat.ban(user.id)
            await message.chat.unban(user.id)
            if cmd == "kickban":
                await db.ban_user(message.chat.id, user.id, reason)
            await db.log_admin_action(message.from_user.id, message.chat.id, "kick", user.id, reason)
            await message.reply(f"👢 {user.full_name} کیک شد.\nدلیل: {reason}")
    except Exception as e:
        await message.reply(f"❌ خطا: {e}")
