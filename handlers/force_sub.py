from aiogram import Router, F, Bot
from aiogram.types import Message, ChatMemberUpdated
from aiogram.filters import Command
from database import db

router = Router()


@router.message(Command("forcesub"))
async def set_force_sub(message: Message):
    chat_member = await message.bot.get_chat_member(message.chat.id, message.from_user.id)
    if chat_member.status not in ("creator", "administrator"):
        return await message.reply("فقط ادمین‌ها می‌تونن تنظیم کنن.")

    args = message.text.replace("/forcesub", "").strip().split()
    if len(args) < 1:
        return await message.reply(
            "برای تنظیم عضویت اجباری:\n\n"
            "/forcesub @channel_username - فعال کردن\n"
            "/forcesub off - غیرفعال کردن\n\n"
            "کاربران باید در کانال عضو باشن تا بتونن از ربات استفاده کنن."
        )

    if args[0].lower() == "off":
        await db.set_group_settings(message.chat.id, force_sub_enabled=0, force_sub_channel="")
        return await message.reply("عضویت اجباری غیرفعال شد.")

    channel = args[0].lstrip("@")
    await db.set_group_settings(message.chat.id, force_sub_enabled=1, force_sub_channel=channel)
    await message.reply(f"عضویت اجباری فعال شد!\nکانال: @{channel}")


@router.message(Command("checksub"))
async def check_subscription(message: Message):
    if message.chat.type not in ("group", "supergroup"):
        return

    settings = await db.get_group_settings(message.chat.id)
    if not settings or not settings["force_sub_enabled"]:
        return

    channel = settings["force_sub_channel"]
    if not channel:
        return

    try:
        member = await message.bot.get_chat_member(f"@{channel}", message.from_user.id)
        if member.status in ("left", "kicked"):
            raise Exception("Not subscribed")
    except Exception:
        await message.reply(
            f"⚠️ برای استفاده از ربات، ابتدا در کانال @{channel} عضو شوید!\n\n"
            f"پس از عضویت، دوباره پیام بدید.",
            disable_web_page_preview=True
        )
        await message.delete()
        return False

    return True
