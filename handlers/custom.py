import re
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from database import db

router = Router()


@router.message(Command("setcmd"))
async def set_custom_command(message: Message):
    chat_member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    if chat_member.status not in ("creator", "administrator"):
        return await message.reply("فقط ادمین‌ها می‌تونن دستور سفارشی بسازن.")

    args = message.text.replace("/setcmd", "").strip().split(None, 1)
    if len(args) < 2:
        return await message.reply(
            "مثال:\n"
            "/setcmd سلام درود بر تو! چطور می‌تونم کمکت کنم؟\n\n"
            "حالا وقتی کسی /سلام بزنه، جواب داده میشه."
        )

    command = args[0].lstrip("/").strip()
    response = args[1].strip()

    if not command or not response:
        return await message.reply("لطفاً دستور و پاسخ رو وارد کنید.")

    await db.add_custom_command(message.chat.id, command, response, message.from_user.id)
    await message.reply(f"دستور /{command} ساخته شد!\nپاسخ: {response}")


@router.message(Command("delcmd"))
async def delete_custom_command(message: Message):
    chat_member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    if chat_member.status not in ("creator", "administrator"):
        return await message.reply("فقط ادمین‌ها می‌تونن دستور رو حذف کنن.")

    args = message.text.replace("/delcmd", "").strip()
    if not args:
        return await message.reply("لطفاً اسم دستور رو بنویسید.\nمثال: /delcmd سلام")

    command = args.lstrip("/").strip()
    if await db.delete_custom_command(message.chat.id, command):
        await message.reply(f"دستور /{command} حذف شد.")
    else:
        await message.reply(f"دستور /{command} پیدا نشد.")


@router.message(Command("listcmds"))
async def list_custom_commands(message: Message):
    commands = await db.list_custom_commands(message.chat.id)
    if not commands:
        return await message.reply("هیچ دستور سفارشی‌ای وجود نداره.")

    text = "📋 دستورات سفارشی:\n\n"
    for cmd in commands:
        text += f"/{cmd['command']} → {cmd['response'][:50]}...\n"
    await message.reply(text)


@router.message(Command("setreply"))
async def set_auto_reply(message: Message):
    chat_member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    if chat_member.status not in ("creator", "administrator"):
        return await message.reply("فقط ادمین‌ها می‌تونن پاسخ خودکار بسازن.")

    args = message.text.replace("/setreply", "").strip().split(None, 1)
    if len(args) < 2:
        return await message.reply(
            "مثال:\n"
            "/setreply سلام خوش اومدی!\n\n"
            "حالا وقتی کسی کلمه «سلام» رو بنویسه، خودکار جواب داده میشه."
        )

    keyword = args[0].strip()
    response = args[1].strip()

    await db.add_auto_reply(message.chat.id, keyword, response, message.from_user.id)
    await message.reply(f"پاسخ خودکار تنظیم شد!\nکلمه: {keyword}\nپاسخ: {response}")


@router.message(Command("delreply"))
async def delete_auto_reply(message: Message):
    chat_member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    if chat_member.status not in ("creator", "administrator"):
        return await message.reply("فقط ادمین‌ها می‌تونن پاسخ خودکار رو حذف کنن.")

    args = message.text.replace("/delreply", "").strip()
    if not args:
        return await message.reply("لطفاً کلمه کلیدی رو بنویسید.\nمثال: /delreply سلام")

    if await db.delete_auto_reply(message.chat.id, args.strip()):
        await message.reply(f"پاسخ خودکار برای «{args.strip()}» حذف شد.")
    else:
        await message.reply(f"پاسخ خودکار برای «{args.strip()}» پیدا نشد.")


@router.message(Command("listreplies"))
async def list_auto_replies(message: Message):
    replies = await db.get_auto_replies(message.chat.id)
    if not replies:
        return await message.reply("هیچ پاسخ خودکاری وجود نداره.")

    text = "🤖 پاسخ‌های خودکار:\n\n"
    for r in replies:
        text += f"«{r['keyword']}» → {r['response'][:50]}...\n"
    await message.reply(text)


# auto-reply checking is now in bot.py ai_chat_handler
