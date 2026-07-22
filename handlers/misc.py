from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import Command
from database import db

router = Router()


@router.message(Command("start"))
async def cmd_start(message: Message):
    if message.chat.type in ("group", "supergroup"):
        return await message.reply(
            "🤖 کُتلت - ربات مدیریت گروه\n\n"
            "📋 دستورات مدیریتی:\n"
            "/rules - نمایش قوانین\n"
            "/setrules - تنظیم قوانین\n"
            "/setwelcome - تنظیم پیام خوشامدگویی\n"
            "/ban - بن کاربر\n"
            "/unban - آنب بن\n"
            "/kick - کیک کاربر\n"
            "/mute - میوت کاربر\n"
            "/unmute - آنمیوت\n"
            "/pin - پین پیام\n"
            "/stats - آمار گروه\n\n"
            "🎭 شخصیت هوش مصنوعی:\n"
            "/setname - تنظیم اسم AI\n"
            "/setprompt - تنظیم پرامپت\n"
            "/toggleai - فعال/غیرفعال کردن AI\n"
            "/showprompt - نمایش تنظیمات\n"
            "/aiexamples - مثال‌های پرامپت\n\n"
            "⚡ دستورات سفارشی:\n"
            "/setcmd - ساخت دستور جدید\n"
            "/delcmd - حذف دستور\n"
            "/listcmds - لیست دستورات\n\n"
            "💬 پاسخ خودکار:\n"
            "/setreply - تنظیم پاسخ خودکار\n"
            "/delreply - حذف پاسخ خودکار\n"
            "/listreplies - لیست پاسخ‌ها\n\n"
            "🤖 چت هوشمند:\n"
            "@کُتلت + پیام - چت با هوش مصنوعی"
        )

    await message.reply(
            "سلام! 👋\nمن کُتلت هستم، ربات مدیریت گروه.\n\n"
        "📋 دستورات ادمین:\n"
        "/ban - بن کاربر (ریپلای)\n"
        "/kick - کیک کاربر (ریپلای)\n"
        "/mute - میوت کاربر (ریپلای)\n"
        "/setrules - تنظیم قوانین\n"
        "/setwelcome - تنظیم خوشامدگویی\n"
        "/setcmd - ساخت دستور سفارشی\n"
        "/setreply - تنظیم پاسخ خودکار\n"
        "/setprompt - تنظیم شخصیت AI\n\n"
        "🤖 چت هوشمند:\n"
        "@کُتلت + پیام - با هوش مصنوعی حرف بزنید"
    )


@router.message(Command("help"))
async def cmd_help(message: Message):
    await cmd_start(message)


@router.message(Command("stats"))
async def cmd_stats(message: Message):
    try:
        member_count = await message.bot.get_chat_member_count(message.chat.id)
        await message.reply(
            f"📊 آمار گروه:\n\n"
            f"👥 تعداد اعضا: {member_count}\n"
            f"📛 نام گروه: {message.chat.title}"
        )
    except Exception as e:
        await message.reply(f"خطا در دریافت آمار: {e}")


@router.message(Command("id"))
async def cmd_id(message: Message):
    await message.reply(f"🆔 آیدی عددی شما:\n<code>{message.from_user.id}</code>")
