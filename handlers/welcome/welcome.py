from aiogram import Router
from aiogram.types import Message
from aiogram.filters import Command

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    await message.reply(
        "سلام! من کتلت هستم 🤖\n"
        "یک بات مدیریت گروه و هوش مصنوعی.\n\n"
        "دستورات:\n"
        "/ai <پیام> - سوال از هوش مصنوعی\n"
        "/ban - بن کاربر\n"
        "/mute - میوت کاربر\n"
        "/warn - اخطار\n"
        "/help - راهنما"
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await message.reply(
        "📚 **راهنمای کتلت**\n\n"
        "**مدیریت گروه:**\n"
        "/ban, /unban, /kick, /mute, /unmute, /warn, /warns, /delwarn, /pin, /purge\n\n"
        "**هوش مصنوعی:**\n"
        "/ai <متن> - سوال از AI\n"
        "یا منشن کن: @kotlet_bot <متن>\n\n"
        "**ادمین:**\n"
        "/ghasemkotlet - پنل مدیریت"
    )
