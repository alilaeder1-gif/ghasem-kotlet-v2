from aiogram import Router, F, Bot
from aiogram.types import Message, ChatMemberUpdated
from aiogram.filters import ChatMemberUpdatedFilter, Command
from database import db
from config import WELCOME_MESSAGE

router = Router()


@router.chat_member(ChatMemberUpdatedFilter(member_status_changed="left -> joined"))
async def on_user_join(event: ChatMemberUpdated):
    chat_id = event.chat.id
    user = event.new_chat_member.user
    settings = await db.get_welcome(chat_id)

    if settings and not settings["is_enabled"]:
        return

    welcome_text = settings["message"] if settings and settings["message"] else WELCOME_MESSAGE
    welcome_text = welcome_text.replace("{name}", user.full_name).replace("{group}", event.chat.title)

    try:
        await event.answer(welcome_text)
    except Exception:
        pass


@router.message(Command("setwelcome"))
async def set_welcome(message: Message):
    chat_member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    if chat_member.status not in ("creator", "administrator"):
        return await message.reply("فقط ادمین‌ها می‌تونن تنظیم کنن.")

    args = message.text.replace("/setwelcome", "").strip()
    if not args:
        return await message.reply(
            "مثال:\n"
            "/setwelcome سلام {name}! به گروه {group} خوش اومدی!\n\n"
            "متغیرها: {name} و {group}\n"
            "برای غیرفعال کردن: /setwelcome off"
        )

    if args.lower() == "off":
        await db.set_welcome(message.chat.id, is_enabled=False)
        return await message.reply("پیام خوشامدگویی غیرفعال شد.")

    await db.set_welcome(message.chat.id, args)
    await message.reply("پیام خوشامدگویی تنظیم شد.")


@router.message(Command("testwelcome"))
async def test_welcome(message: Message):
    settings = await db.get_welcome(message.chat.id)
    welcome_text = settings["message"] if settings and settings["message"] else WELCOME_MESSAGE
    welcome_text = welcome_text.replace("{name}", message.from_user.full_name).replace("{group}", message.chat.title)
    await message.reply(welcome_text)
