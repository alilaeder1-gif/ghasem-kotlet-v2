from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from database import db

router = Router()


@router.message(Command("rules"))
async def show_rules(message: Message):
    rules = await db.get_rules(message.chat.id)
    if not rules:
        return await message.reply("قوانینی برای این گروه تنظیم نشده.\nادمین‌ها می‌تونن با /setrules قوانین رو تنظیم کنن.")
    await message.reply(f"📋 قوانین گروه:\n\n{rules}")


@router.message(Command("setrules"))
async def set_rules(message: Message):
    chat_member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    if chat_member.status not in ("creator", "administrator"):
        return await message.reply("فقط ادمین‌ها می‌تونن قوانین رو تنظیم کنن.")

    rules_text = message.text.replace("/setrules", "").strip()
    if not rules_text:
        return await message.reply("لطفاً متن قوانین رو بنویسید.\nمثال:\n/setrules 1. اسپم ممنوع\n2. توهین ممنوع")

    await db.set_rules(message.chat.id, rules_text)
    await message.reply("قوانین با موفقیت ذخیره شد.")


@router.message(Command("clearrules"))
async def clear_rules(message: Message):
    chat_member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    if chat_member.status not in ("creator", "administrator"):
        return await message.reply("فقط ادمین‌ها می‌تونن قوانین رو پاک کنن.")

    await db.set_rules(message.chat.id, "")
    await message.reply("قوانین پاک شد.")
